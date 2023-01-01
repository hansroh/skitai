import pytest
skip_grpc = False
try:
    from examples.services import route_guide_pb2
    from examples.services.route_guide_pb2_grpc import RouteGuideStub
except ImportError:
    skip_grpc = True
import os
import time

# @pytest.mark.skip
def test_grpc (launch):
    if skip_grpc:
        return
    try: import grpc
    except ImportError: return

    server = "127.0.0.1:30371"
    with launch ("./examples/app.py") as engine:
        with grpc.insecure_channel(server) as channel:
            stub = RouteGuideStub (channel)

            point = route_guide_pb2.Point (latitude=409146138, longitude=-746188906)
            feature = stub.GetFeature (point)
            assert isinstance (feature, route_guide_pb2.Feature)

            # response streaming
            rectangle = route_guide_pb2.Rectangle(
                lo=route_guide_pb2.Point(latitude=400000000, longitude=-750000000),
                hi=route_guide_pb2.Point(latitude=420000000, longitude=-730000000))
            for idx, feature in enumerate (stub.ListFeatures(rectangle)):
                assert hasattr (feature, 'name')
            assert idx > 80
