import optpaillier
import optthpaillier

pai_sklist, pai_pk_optthpaillier = optthpaillier.pai_th_keygen(4)
pai_sk, pai_pk = optpaillier.pai_keygen()
print(1)
print(pai_sklist)
print(2)
print(pai_pk_optthpaillier)
print(3)
print(pai_sk)
print(4)
print(pai_pk)
