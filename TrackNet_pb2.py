# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: TrackNet.proto
# Protobuf Python Version: 4.25.3
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0eTrackNet.proto\x12\x08TrackNet\"\xd0\x02\n\x05Track\x12\x17\n\njunction_a\x18\x01 \x01(\tH\x00\x88\x01\x01\x12\x17\n\njunction_b\x18\x02 \x01(\tH\x01\x88\x01\x01\x12\x0f\n\x02id\x18\x03 \x01(\tH\x02\x88\x01\x01\x12+\n\x06trains\x18\x04 \x03(\x0b\x32\x1b.TrackNet.Track.TrainsEntry\x12\x30\n\tcondition\x18\x05 \x01(\x0e\x32\x18.TrackNet.TrackConditionH\x03\x88\x01\x01\x12(\n\x05speed\x18\x06 \x01(\x0e\x32\x14.TrackNet.TrainSpeedH\x04\x88\x01\x01\x1a>\n\x0bTrainsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\x1e\n\x05value\x18\x02 \x01(\x0b\x32\x0f.TrackNet.Train:\x02\x38\x01\x42\r\n\x0b_junction_aB\r\n\x0b_junction_bB\x05\n\x03_idB\x0c\n\n_conditionB\x08\n\x06_speed\"\x9e\x02\n\x08Junction\x12\x0f\n\x02id\x18\x01 \x01(\tH\x00\x88\x01\x01\x12\x34\n\tneighbors\x18\x02 \x03(\x0b\x32!.TrackNet.Junction.NeighborsEntry\x12;\n\rparked_trains\x18\x03 \x03(\x0b\x32$.TrackNet.Junction.ParkedTrainsEntry\x1a\x41\n\x0eNeighborsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\x1e\n\x05value\x18\x02 \x01(\x0b\x32\x0f.TrackNet.Track:\x02\x38\x01\x1a\x44\n\x11ParkedTrainsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\x1e\n\x05value\x18\x02 \x01(\x0b\x32\x0f.TrackNet.Train:\x02\x38\x01\x42\x05\n\x03_id\"\xac\x01\n\x05Route\x12%\n\tjunctions\x18\x01 \x03(\x0b\x32\x12.TrackNet.Junction\x12#\n\x16\x63urrent_junction_index\x18\x02 \x01(\x05H\x00\x88\x01\x01\x12,\n\x0b\x64\x65stination\x18\x03 \x01(\x0b\x32\x12.TrackNet.JunctionH\x01\x88\x01\x01\x42\x19\n\x17_current_junction_indexB\x0e\n\x0c_destination\"\xb0\x02\n\x08Location\x12\x1e\n\x11\x66ront_junction_id\x18\x01 \x01(\tH\x00\x88\x01\x01\x12\x1b\n\x0e\x66ront_track_id\x18\x02 \x01(\tH\x01\x88\x01\x01\x12\x1b\n\x0e\x66ront_position\x18\x03 \x01(\x02H\x02\x88\x01\x01\x12\x1d\n\x10\x62\x61\x63k_junction_id\x18\x04 \x01(\tH\x03\x88\x01\x01\x12\x1a\n\rback_track_id\x18\x05 \x01(\tH\x04\x88\x01\x01\x12\x1a\n\rback_position\x18\x06 \x01(\x02H\x05\x88\x01\x01\x42\x14\n\x12_front_junction_idB\x11\n\x0f_front_track_idB\x11\n\x0f_front_positionB\x13\n\x11_back_junction_idB\x10\n\x0e_back_track_idB\x10\n\x0e_back_position\"\x96\x03\n\x05Train\x12\x0f\n\x02id\x18\x01 \x01(\tH\x00\x88\x01\x01\x12\x13\n\x06length\x18\x02 \x01(\x02H\x01\x88\x01\x01\x12.\n\x05state\x18\x03 \x01(\x0e\x32\x1a.TrackNet.Train.TrainStateH\x02\x88\x01\x01\x12)\n\x08location\x18\x04 \x01(\x0b\x32\x12.TrackNet.LocationH\x03\x88\x01\x01\x12#\n\x05route\x18\x05 \x01(\x0b\x32\x0f.TrackNet.RouteH\x04\x88\x01\x01\x12,\n\x0b\x64\x65stination\x18\x06 \x01(\x0b\x32\x12.TrackNet.JunctionH\x05\x88\x01\x01\x12\x12\n\x05speed\x18\x07 \x01(\x05H\x06\x88\x01\x01\"X\n\nTrainState\x12\x0b\n\x07RUNNING\x10\x00\x12\x08\n\x04SLOW\x10\x01\x12\x0b\n\x07STOPPED\x10\x02\x12\n\n\x06PARKED\x10\x03\x12\x0b\n\x07PARKING\x10\x04\x12\r\n\tUNPARKING\x10\x05\x42\x05\n\x03_idB\t\n\x07_lengthB\x08\n\x06_stateB\x0b\n\t_locationB\x08\n\x06_routeB\x0e\n\x0c_destinationB\x08\n\x06_speed\"\xf3\x01\n\x07Railmap\x12\x33\n\tjunctions\x18\x01 \x03(\x0b\x32 .TrackNet.Railmap.JunctionsEntry\x12-\n\x06tracks\x18\x02 \x03(\x0b\x32\x1d.TrackNet.Railmap.TracksEntry\x1a\x44\n\x0eJunctionsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12!\n\x05value\x18\x02 \x01(\x0b\x32\x12.TrackNet.Junction:\x02\x38\x01\x1a>\n\x0bTracksEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\x1e\n\x05value\x18\x02 \x01(\x0b\x32\x0f.TrackNet.Track:\x02\x38\x01\"\xd3\x01\n\x07Railway\x12#\n\x03map\x18\x01 \x01(\x0b\x32\x11.TrackNet.RailmapH\x00\x88\x01\x01\x12-\n\x06trains\x18\x02 \x03(\x0b\x32\x1d.TrackNet.Railway.TrainsEntry\x12\x1a\n\rtrain_counter\x18\x03 \x01(\x05H\x01\x88\x01\x01\x1a>\n\x0bTrainsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\x1e\n\x05value\x18\x02 \x01(\x0b\x32\x0f.TrackNet.Train:\x02\x38\x01\x42\x06\n\x04_mapB\x10\n\x0e_train_counter\"j\n\rRailwayUpdate\x12\'\n\x07railway\x18\x01 \x01(\x0b\x32\x11.TrackNet.RailwayH\x00\x88\x01\x01\x12\x16\n\ttimestamp\x18\x02 \x01(\tH\x01\x88\x01\x01\x42\n\n\x08_railwayB\x0c\n\n_timestamp\"\xeb\x02\n\x0eServerResponse\x12\x15\n\x08\x63lientIP\x18\x01 \x01(\tH\x00\x88\x01\x01\x12\x17\n\nclientPort\x18\x02 \x01(\tH\x01\x88\x01\x01\x12#\n\x05train\x18\x03 \x01(\x0b\x32\x0f.TrackNet.TrainH\x02\x88\x01\x01\x12:\n\x06status\x18\x04 \x01(\x0e\x32%.TrackNet.ServerResponse.UpdateStatusH\x03\x88\x01\x01\x12\'\n\tnew_route\x18\x05 \x01(\x0b\x32\x0f.TrackNet.RouteH\x04\x88\x01\x01\x12\x12\n\x05speed\x18\x06 \x01(\x05H\x05\x88\x01\x01\"B\n\x0cUpdateStatus\x12\x10\n\x0c\x43HANGE_SPEED\x10\x00\x12\x0b\n\x07REROUTE\x10\x01\x12\x08\n\x04STOP\x10\x02\x12\t\n\x05\x43LEAR\x10\x03\x42\x0b\n\t_clientIPB\r\n\x0b_clientPortB\x08\n\x06_trainB\t\n\x07_statusB\x0c\n\n_new_routeB\x08\n\x06_speed\"\xcd\x02\n\x0b\x43lientState\x12\x15\n\x08\x63lientIP\x18\x01 \x01(\tH\x00\x88\x01\x01\x12\x17\n\nclientPort\x18\x02 \x01(\tH\x01\x88\x01\x01\x12#\n\x05train\x18\x03 \x01(\x0b\x32\x0f.TrackNet.TrainH\x02\x88\x01\x01\x12\x12\n\x05speed\x18\x04 \x01(\x02H\x03\x88\x01\x01\x12)\n\x08location\x18\x05 \x01(\x0b\x32\x12.TrackNet.LocationH\x04\x88\x01\x01\x12\x30\n\tcondition\x18\x06 \x01(\x0e\x32\x18.TrackNet.TrackConditionH\x05\x88\x01\x01\x12#\n\x05route\x18\x07 \x01(\x0b\x32\x0f.TrackNet.RouteH\x06\x88\x01\x01\x42\x0b\n\t_clientIPB\r\n\x0b_clientPortB\x08\n\x06_trainB\x08\n\x06_speedB\x0b\n\t_locationB\x0c\n\n_conditionB\x08\n\x06_route\"\"\n\x0eRoleAssignment\x12\x10\n\x08isMaster\x18\x01 \x01(\x08\"+\n\rServerDetails\x12\x0c\n\x04host\x18\x01 \x01(\t\x12\x0c\n\x04port\x18\x02 \x01(\x05\"`\n\x10ServerAssignment\x12\x15\n\x08isMaster\x18\x01 \x01(\x08H\x00\x88\x01\x01\x12(\n\x07servers\x18\x02 \x03(\x0b\x32\x17.TrackNet.ServerDetailsB\x0b\n\t_isMaster\"d\n\x08Response\x12*\n\x04\x63ode\x18\x01 \x01(\x0e\x32\x17.TrackNet.Response.CodeH\x00\x88\x01\x01\"#\n\x04\x43ode\x12\x07\n\x03\x41\x43K\x10\x00\x12\x07\n\x03NAK\x10\x01\x12\t\n\x05\x45RROR\x10\x02\x42\x07\n\x05_code\"\xee\x03\n\x0eInitConnection\x12\x18\n\x0bisHeartBeat\x18\x01 \x01(\x08H\x00\x88\x01\x01\x12\x34\n\x06sender\x18\x02 \x01(\x0e\x32\x1f.TrackNet.InitConnection.SenderH\x01\x88\x01\x01\x12\x30\n\x0c\x63lient_state\x18\x03 \x01(\x0b\x32\x15.TrackNet.ClientStateH\x02\x88\x01\x01\x12\x36\n\x0fserver_response\x18\x04 \x01(\x0b\x32\x18.TrackNet.ServerResponseH\x03\x88\x01\x01\x12\x34\n\x0erailway_update\x18\x05 \x01(\x0b\x32\x17.TrackNet.RailwayUpdateH\x04\x88\x01\x01\x12:\n\x14slave_server_details\x18\x06 \x01(\x0b\x32\x17.TrackNet.ServerDetailsH\x05\x88\x01\x01\"D\n\x06Sender\x12\x11\n\rSERVER_MASTER\x10\x00\x12\x10\n\x0cSERVER_SLAVE\x10\x01\x12\n\n\x06\x43LIENT\x10\x02\x12\t\n\x05PROXY\x10\x03\x42\x0e\n\x0c_isHeartBeatB\t\n\x07_senderB\x0f\n\r_client_stateB\x12\n\x10_server_responseB\x11\n\x0f_railway_updateB\x17\n\x15_slave_server_details*#\n\x0eTrackCondition\x12\x07\n\x03\x42\x41\x44\x10\x00\x12\x08\n\x04GOOD\x10\x01*.\n\nTrainSpeed\x12\x0b\n\x07STOPPED\x10\x00\x12\x08\n\x04SLOW\x10\x64\x12\t\n\x04\x46\x41ST\x10\xc8\x01\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'TrackNet_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_TRACK_TRAINSENTRY']._options = None
  _globals['_TRACK_TRAINSENTRY']._serialized_options = b'8\001'
  _globals['_JUNCTION_NEIGHBORSENTRY']._options = None
  _globals['_JUNCTION_NEIGHBORSENTRY']._serialized_options = b'8\001'
  _globals['_JUNCTION_PARKEDTRAINSENTRY']._options = None
  _globals['_JUNCTION_PARKEDTRAINSENTRY']._serialized_options = b'8\001'
  _globals['_RAILMAP_JUNCTIONSENTRY']._options = None
  _globals['_RAILMAP_JUNCTIONSENTRY']._serialized_options = b'8\001'
  _globals['_RAILMAP_TRACKSENTRY']._options = None
  _globals['_RAILMAP_TRACKSENTRY']._serialized_options = b'8\001'
  _globals['_RAILWAY_TRAINSENTRY']._options = None
  _globals['_RAILWAY_TRAINSENTRY']._serialized_options = b'8\001'
  _globals['_TRACKCONDITION']._serialized_start=3595
  _globals['_TRACKCONDITION']._serialized_end=3630
  _globals['_TRAINSPEED']._serialized_start=3632
  _globals['_TRAINSPEED']._serialized_end=3678
  _globals['_TRACK']._serialized_start=29
  _globals['_TRACK']._serialized_end=365
  _globals['_TRACK_TRAINSENTRY']._serialized_start=242
  _globals['_TRACK_TRAINSENTRY']._serialized_end=304
  _globals['_JUNCTION']._serialized_start=368
  _globals['_JUNCTION']._serialized_end=654
  _globals['_JUNCTION_NEIGHBORSENTRY']._serialized_start=512
  _globals['_JUNCTION_NEIGHBORSENTRY']._serialized_end=577
  _globals['_JUNCTION_PARKEDTRAINSENTRY']._serialized_start=579
  _globals['_JUNCTION_PARKEDTRAINSENTRY']._serialized_end=647
  _globals['_ROUTE']._serialized_start=657
  _globals['_ROUTE']._serialized_end=829
  _globals['_LOCATION']._serialized_start=832
  _globals['_LOCATION']._serialized_end=1136
  _globals['_TRAIN']._serialized_start=1139
  _globals['_TRAIN']._serialized_end=1545
  _globals['_TRAIN_TRAINSTATE']._serialized_start=1380
  _globals['_TRAIN_TRAINSTATE']._serialized_end=1468
  _globals['_RAILMAP']._serialized_start=1548
  _globals['_RAILMAP']._serialized_end=1791
  _globals['_RAILMAP_JUNCTIONSENTRY']._serialized_start=1659
  _globals['_RAILMAP_JUNCTIONSENTRY']._serialized_end=1727
  _globals['_RAILMAP_TRACKSENTRY']._serialized_start=1729
  _globals['_RAILMAP_TRACKSENTRY']._serialized_end=1791
  _globals['_RAILWAY']._serialized_start=1794
  _globals['_RAILWAY']._serialized_end=2005
  _globals['_RAILWAY_TRAINSENTRY']._serialized_start=242
  _globals['_RAILWAY_TRAINSENTRY']._serialized_end=304
  _globals['_RAILWAYUPDATE']._serialized_start=2007
  _globals['_RAILWAYUPDATE']._serialized_end=2113
  _globals['_SERVERRESPONSE']._serialized_start=2116
  _globals['_SERVERRESPONSE']._serialized_end=2479
  _globals['_SERVERRESPONSE_UPDATESTATUS']._serialized_start=2340
  _globals['_SERVERRESPONSE_UPDATESTATUS']._serialized_end=2406
  _globals['_CLIENTSTATE']._serialized_start=2482
  _globals['_CLIENTSTATE']._serialized_end=2815
  _globals['_ROLEASSIGNMENT']._serialized_start=2817
  _globals['_ROLEASSIGNMENT']._serialized_end=2851
  _globals['_SERVERDETAILS']._serialized_start=2853
  _globals['_SERVERDETAILS']._serialized_end=2896
  _globals['_SERVERASSIGNMENT']._serialized_start=2898
  _globals['_SERVERASSIGNMENT']._serialized_end=2994
  _globals['_RESPONSE']._serialized_start=2996
  _globals['_RESPONSE']._serialized_end=3096
  _globals['_RESPONSE_CODE']._serialized_start=3052
  _globals['_RESPONSE_CODE']._serialized_end=3087
  _globals['_INITCONNECTION']._serialized_start=3099
  _globals['_INITCONNECTION']._serialized_end=3593
  _globals['_INITCONNECTION_SENDER']._serialized_start=3417
  _globals['_INITCONNECTION_SENDER']._serialized_end=3485
# @@protoc_insertion_point(module_scope)
