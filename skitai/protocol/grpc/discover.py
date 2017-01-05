from google.protobuf import descriptor_pb2
from google.protobuf import descriptor_pool
import phonebook_pb2 as pb

proto = descriptor_pb2.FileDescriptorProto.FromString(
    phonebook_pb2.DESCRIPTOR.serialized_pb
)

pool = descriptor_pool.Default()
print (pool.FindByName ("proto.phonebook"))

proto.service [0].method[0]
proto.service [0].method[0].name
'getBook'
proto.service [0].method[0].input_type
'.tutorial.null'

book = pb.Book ()
p = book.person.add ()
p.name = "Hans Roh"
p.id = 1
phone = p.phone.add ()
phone.type = 1
phone.number = "4602-1165"

mbook = book.SerializeToString ()
print (mbook)

book = pb.Book ()
book.ParseFromString (mbook)

print (book)
