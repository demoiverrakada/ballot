import argparse
import ast
import hashlib
import json
import qrcode
import pymongo
from pymongo import MongoClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from klefki.algebra.concrete import EllipticCurveGroupSecp256k1 as Curve
from klefki.algebra.concrete import FiniteFieldCyclicSecp256k1 as CF
from klefki.algebra.concrete import FiniteFieldSecp256k1 as F
from klefki.algebra.utils import randfield
import random
import string
from collections import deque

G = Curve.G
s = bytes.fromhex("0479be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8")
x = int(hashlib.sha256(s).hexdigest(), 16)
H = Curve.lift_x(F(x))

def connect_to_mongodb():
    # Connect to MongoDB
    client = MongoClient('mongodb+srv://demoiverrakada:H*jwNx399A*4898@cluster0.morsxl9.mongodb.net/')
    # Create or use existing database
    db = client['test']
    # Create or use existing collection
    collection = db['receipts']
    return collection

def generate_short_id(length=8):
    # Generate a short random ID with letters and digits
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def ecc(collection, candidate_list, commitment_pad, rand_factor):
    
    commitments = []

    # Convert candidate_random_factors to hexadecimal strings
    commitment_pad = [int(factor) for factor in commitment_pad]

    # Generate a unique identifier for this document
    commitment_identifier = generate_short_id()
    commitments2 = []

    # Generate commitments for each candidate
    for i, candidate in enumerate(candidate_list):
        rid = commitment_pad[i]
        r_rid = rand_factor
        u = randfield(CF)
        r_u = randfield(CF)
        C_rid = (G ** rid) * (H ** r_rid)
        C_u = (G ** u) * (H ** r_u)
        rid = str(rid)
        r_rid = str(r_rid)
        u = str(u)
        r_u = str(r_u)
        C_ridX = str(C_rid.x)
        C_ridY = str(C_rid.y)
        C_rid_str2 = C_ridX + C_ridY
        C_rid_str = tuple([C_ridX, C_ridY])

        # Append commitment to list
        commitments2.append(f"{C_rid_str2}")
        commitments.append(C_rid_str)

    # Convert commitments to JSON array string
    commitments_json = json.dumps(commitments)

    # Calculate SHA256 hash of the JSON array string
    password = ''.join(commitments2)
    sha256_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    # Insert data into MongoDB
    collection.insert_one({
        'commitment_identifier': commitment_identifier,  # Use the unique identifier
        'ballot_id': sha256_hash,
        'candlist': candidate_list,
        'commitment_pad': [str(factor) for factor in commitment_pad],
        'rand_factor': str(rand_factor),
        'commitments': commitments,
        'accessed': False
    })

    # Generate QR code for JSON array string
    qr = qrcode.make(commitments_json, version=1)

    return qr, sha256_hash, commitment_identifier
    
def create_pdf(file_path, candidate_list, qr, ballot_id):
    # Create a PDF canvas with A4 size
    c = canvas.Canvas(file_path, pagesize=letter)

    # Set font and size for the titles
    c.setFont("Helvetica", 16)

    # Draw a vertical line to divide the page
    c.line(300, 0, 300, 800)

    # Draw titles and strings on the left half
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 450, "Candidates")  # Adjusted y-coordinate
    c.setFont("Helvetica", 12)
    choices = candidate_list
    y_position = 400  # Adjusted y-coordinate

    for i, choice in enumerate(choices, start=1):
        c.drawString(120, y_position, f"{i}. {choice}")
        y_position -= 50  # Adjust the gap between choices

    # Draw titles and strings on the right half
    c.setFont("Helvetica-Bold", 16)
    c.drawString(400, 450, "Commitments")  # Adjusted y-coordinate
    c.setFont("Helvetica", 12)

    # Draw QR code for commitments
    qr_size = 200
    c.drawInlineImage(qr, 370 + (150 - qr_size) / 2, 250, width=qr_size, height=qr_size)  # Adjusted y-coordinate

    # Draw the ballot ID at the bottom left
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 30, f"Ballot ID: {ballot_id}")  # Adjusted x and y coordinates

    # Save the canvas to a PDF file
    c.save()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate PDF with candidate list and commitments.')

    # Prompt the user for the number of candidates
    num_candidates = int(input("Enter the number of candidates: "))
    candidate_list = [input(f"Enter name of candidate {i + 1}: ") for i in range(num_candidates)]

    # Number of ballots to generate
    num_ballots = int(input("Enter the number of ballots to be generated: "))

    # Circular permutation of the candidate list
    candidate_deque = deque(candidate_list)

    for ballot_num in range(1, num_ballots + 1):
        # Rotate the candidate deque for each ballot
        candidate_deque.rotate(1)

        # Convert deque back to list
        rotated_candidate_list = list(candidate_deque)

        # Random factors and finalized randomness factor
        commitment_pad = [randfield(CF) for _ in range(num_candidates)]
        commitment_pad = [int(factor.value) for factor in commitment_pad]
        rand_factor = randfield(CF)

        output_file = f"output{ballot_num}.pdf"
        collection = connect_to_mongodb()
        qr, sha256_hash, ballot_id = ecc(collection, rotated_candidate_list, commitment_pad, rand_factor)
        create_pdf(output_file, rotated_candidate_list, qr, ballot_id)
        print(f"Ballot {ballot_num} generated successfully")

