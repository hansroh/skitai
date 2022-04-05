import pytest
from examples.services import route_guide_pb2
import os
import time

# @pytest.mark.skip
def test_grpc (launch):
    try: import grpc
    except ImportError: return

    server = "127.0.0.1:30371"
    with launch ("./examples/app.py") as engine:
        with grpc.insecure_channel(server) as channel:
            stub = route_guide_pb2.RouteGuideStub (channel)

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


# @pytest.mark.skip
def test_grpc_request_stream (launch):
    # if os.getenv ("GITLAB_USER_NAME"):
    #     return
    try: import grpc
    except ImportError: return

    def point_iter ():
        for i in range (30):
            print ('send', i)
            yield route_guide_pb2.Point (latitude=409146138, longitude=-746188906)
            time.sleep (0.2)

    server = "127.0.0.1:30371"
    with launch ("./examples/app.py") as engine:
        with grpc.insecure_channel(server) as channel:
            stub = route_guide_pb2.RouteGuideStub (channel)
            # request streaming
            summary = stub.RecordRoute (point_iter ())
            assert isinstance (summary, route_guide_pb2.RouteSummary)
            assert summary.point_count == 30


# @pytest.mark.skip
def test_grpc_request_bistream (launch):
    # if os.getenv ("GITLAB_USER_NAME"):
    #     return
    try: import grpc
    except ImportError: return

    def make_route_note(message, latitude, longitude):
        return route_guide_pb2.RouteNote(
            message=message,
            location=route_guide_pb2.Point(latitude=latitude, longitude=longitude))

    def generate_messages():
        messages = [
            make_route_note("First message", 0, 0),
            make_route_note("Second message", 0, 1),
            make_route_note("Third message", 1, 0),
            make_route_note("Fourth message", 0, 0),
            make_route_note("Fifth message", 1, 0),
        ] * 3
        for i, msg in enumerate (messages):
            print ('send', i)
            time.sleep (0.2)
            yield msg

    server = "127.0.0.1:30371"
    with launch ("./examples/app.py") as engine:
        with grpc.insecure_channel(server) as channel:
            stub = route_guide_pb2.RouteGuideStub (channel)

            # bidirectional
            for idx, response in enumerate (stub.RouteChat(generate_messages())):
                print ('  - recv', idx)
                assert hasattr (response, 'message')
                assert hasattr (response, 'location')
            assert idx == 32
