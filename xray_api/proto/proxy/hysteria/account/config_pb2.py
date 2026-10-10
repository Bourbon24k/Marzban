"""Xray v26.3.27 proxy/hysteria/account/config.proto (wire-compatible)."""
from google.protobuf import descriptor_pb2, descriptor_pool, message, reflection

_spec = descriptor_pb2.FileDescriptorProto(
    name="proxy/hysteria/account/config.proto",
    package="xray.proxy.hysteria.account", syntax="proto3")
_account = _spec.message_type.add(name="Account")
_account.field.add(name="auth", number=1, label=1, type=9)
DESCRIPTOR = descriptor_pool.Default().AddSerializedFile(_spec.SerializeToString())
Account = reflection.GeneratedProtocolMessageType("Account", (message.Message,), {
    "DESCRIPTOR": DESCRIPTOR.message_types_by_name["Account"], "__module__": __name__})
