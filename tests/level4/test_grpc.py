
def test_grpc (launch):
    from examples.services import route_guide_pb2
    try:
        import grpc
    except ImportError:
        return

    server = "127.0.0.1:30371"
    with launch ("./examples/app.py") as engine:
        with grpc.insecure_channel(server) as channel:
            stub = route_guide_pb2.RouteGuideStub (channel)
            point = route_guide_pb2.Point (latitude=409146138, longitude=-746188906)
            feature = stub.GetFeature (point)
            assert isinstance (feature, route_guide_pb2.Feature)
