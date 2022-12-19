from atila import Atila
import time
import asyncio
try:
    from services import route_guide_pb2
except ImportError:
    from services import route_guide_pb2_v3 as route_guide_pb2
from grpc_route_guide import get_feature, get_distance, _jsondb, db

app = Atila (__name__)
app.debug = True
app.use_reloader = True

@app.route ("/GetFeature")
async def GetFeature (context, point):
	feature = get_feature(db, point)
	await asyncio.sleep (0.5)
	if feature is None:
		return route_guide_pb2.Feature(name="", location=point)
	else:
		return feature

@app.route ("/ListFeatures", stream = True)
async def ListFeatures (context, rectangle):
	left = min(rectangle.lo.longitude, rectangle.hi.longitude)
	right = max(rectangle.lo.longitude, rectangle.hi.longitude)
	top = max(rectangle.lo.latitude, rectangle.hi.latitude)
	bottom = min(rectangle.lo.latitude, rectangle.hi.latitude)
	for feature in db:
		if (feature.location.longitude >= left and feature.location.longitude <= right and feature.location.latitude >= bottom and feature.location.latitude <= top):
			await context.stream.send (feature)

@app.route ("/RecordRoute", stream = True)
async def RecordRoute (context, point_iter):
	point_count = 0
	feature_count = 0
	distance = 0.0
	prev_point = None

	start_time = time.time()
	while 1:
		point = await point_iter.receive ()
		print (point)
		if not point:
			break
		point_count += 1
		if get_feature(db, point):
			feature_count += 1
		if prev_point:
			distance += get_distance(prev_point, point)
		prev_point = point

	elapsed_time = time.time() - start_time
	return route_guide_pb2.RouteSummary (
		point_count=point_count,
		feature_count=feature_count,
		distance=int(distance),
		elapsed_time=int(elapsed_time)
	)

@app.route ("/RouteChat", stream = True)
async def RouteChat (context, note_iter):
	prev_notes = []
	while 1:
		new_note = await note_iter.receive ()
		if not new_note:
			break
		for prev_note in prev_notes:
			if prev_note.location == new_note.location:
				await context.stream.send (prev_note)
		prev_notes.append(new_note)

@app.route ("/test")
def test (context):
	point = route_guide_pb2.Point (latitude=409146138, longitude=-746188906)
	return str (point)

@app.route ("/")
def index (context):
	return "<h1>Route Guide Async Version<h1>"


if __name__ == "__main__":
	import skitai
	skitai.mount ("/routeguide.RouteGuide", app)
	skitai.run (address = "0.0.0.0", port = 30371, tasks = 4)
