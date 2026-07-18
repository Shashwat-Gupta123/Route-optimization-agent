Openrouteservice
Introduction
This is the openrouteservice API documentation for ORS Core-Version 9.9.0. Documentations for older Core-Versions can be rendered with the Swagger-Editor.

Authentication
lock User SecurityAPI Key help
Query-Parameter:
For GET requests add your API Key as the value of the api_key parameter or use the Authorization-Header.

Authorization-Header:
For POST & GET requests add your API Key as the value of the Authorization header.

Reference
Directions Service
Get directions for different modes of transport

/v2/directions/{profile}
GET
Directions Service
navigate_next
lockQuery-ParameterAuthorization-Header
Get a basic route between two points with the profile provided. Returned response is in GeoJSON format. This method does not accept any request body or parameters other than profile, start coordinate, and end coordinate.

/v2/directions/{profile}
POST
Directions Service
navigate_next
lockAuthorization-Header
Returns a route between two or more locations for a selected profile and its settings as JSON

/v2/directions/{profile}/json
POST
Directions Service JSON
navigate_next
lockAuthorization-Header
Returns a route between two or more locations for a selected profile and its settings as JSON

/v2/directions/{profile}/gpx
POST
Directions Service GPX
navigate_next
lockAuthorization-Header
Returns a route between two or more locations for a selected profile and its settings as GPX. The schema can be found here

/v2/directions/{profile}/geojson
POST
Directions Service GeoJSON
navigate_next
lockAuthorization-Header
Returns a route between two or more locations for a selected profile and its settings as GeoJSON

Export Service
Export the base graph for different modes of transport

/v2/export/{profile}
POST
Export Service
navigate_next
lockAuthorization-Header
Returns a list of points, edges and weights within a given bounding box for a selected profile as JSON. This method does not accept any request body or parameters other than profile, start coordinate, and end coordinate.

/v2/export/{profile}/topojson
POST
Export Service TopoJSON
navigate_next
lockAuthorization-Header
Returns a list of edges, edge properties, and their topology within a given bounding box for a selected profile.

/v2/export/{profile}/json
POST
Export Service JSON
navigate_next
lockAuthorization-Header
Returns a list of points, edges and weights within a given bounding box for a selected profile as JSON.

Isochrones Service
Obtain areas of reachability from given locations

/v2/isochrones/{profile}
POST
Isochrones Service
navigate_next
lockAuthorization-Header
The Isochrone Service supports time and distance analyses for one single or multiple locations.
You may also specify the isochrone interval or provide multiple exact isochrone range values.
This service allows the same range of profile options as the /directions endpoint,
which help you to further customize your request to obtain a more detailed reachability area response.

Matrix Service
Obtain one-to-many, many-to-one and many-to-many matrices for time and distance

/v2/matrix/{profile}
POST
Matrix Service
navigate_next
lockAuthorization-Header
Returns duration or distance matrix for multiple source and destination points.
By default a square duration matrix is returned where every point in locations is paired with each other. The result is null if a value can’t be determined.

Snapping Service
Snap coordinates to the road network.

/v2/snap/{profile}
POST
Snapping Service
navigate_next
lockAuthorization-Header
Returns a list of points snapped to the nearest edge in the routing graph. In case an appropriate
snapping point cannot be found within the specified search radius, “null” is returned.

/v2/snap/{profile}/json
POST
Snapping Service JSON
navigate_next
lockAuthorization-Header
Returns a list of points snapped to the nearest edge in the routing graph. In case an appropriate
snapping point cannot be found within the specified search radius, “null” is returned.

/v2/snap/{profile}/geojson
POST
Snapping Service GeoJSON
navigate_next
lockAuthorization-Header
Returns a GeoJSON FeatureCollection of points snapped to the nearest edge in the routing graph.
In case an appropriate snapping point cannot be found within the specified search radius,
it is omitted from the features array. The features provide the ‘source_id’ property, to match
the results with the input location array (IDs start at 0).

Pois
Obtain POIs of an area

/pois
POST
Pois Service
navigate_next
lockAuthorization-Header
Returns points of interest in the area surrounding a geometry which can either be a bounding box, polygon or buffered linestring or point.
Find more examples on github.

Optimization
Optimize routes for vehicle fleets

/optimization
POST
Optimization Service
navigate_next
lockAuthorization-Header
The optimization endpoint solves Vehicle Routing Problems and can be used to schedule multiple vehicles and jobs, respecting time windows, capacities and required skills.

This service is based on the excellent Vroom project. Please also consult its API documentation.

General Info:

The expected order for all coordinates arrays is [lon, lat]
All timings are in seconds
All distances are in meters
A time_window object is a pair of timestamps in the form [start, end]
Elevation
Returns elevation for point or line geometries by building 3D geometries from freely available data sources.

/elevation/line
POST
Elevation Line Service
navigate_next
lockAuthorization-Header
This endpoint can take planar 2D line objects and enrich them with elevation from a variety of datasets.

The input and output formats are:

GeoJSON
Polyline
Google’s Encoded polyline with coordinate precision 5 or 6
Example:

  # POST LineString as polyline
  curl -XPOST https://api.openrouteservice.org/elevation/line
    -H 'Content-Type: application/json' \
    -H 'Authorization: INSERT_YOUR_KEY
    -d '{
      "format_in": "polyline",
      "format_out": "encodedpolyline5",
      "geometry": [[13.349762, 38.112952],
                   [12.638397, 37.645772]]
        }'
/elevation/point
GET
Elevation Point Service
navigate_next
lockQuery-ParameterAuthorization-Header
This endpoint can take a 2D point and enrich it with elevation from a variety of datasets.

The output formats are:

GeoJSON
Point
Example:

  # GET point
  curl -XGET https://localhost:5000/elevation/point?geometry=13.349762,38.11295
/elevation/point
POST
Elevation Point Service
navigate_next
lockAuthorization-Header
This endpoint can take a 2D point and enrich it with elevation from a variety of datasets.

The input and output formats are:

GeoJSON
Point
Example:

  # POST point as GeoJSON
  # https://api.openrouteservice.org/elevation/point?api_key=YOUR-KEY
  {
    "format_in": "geojson",
    "format_out": "geojson",
    "geometry": {
      "coordinates": [13.349762, 38.11295],
      "type": "Point"
    }
  }
Geocode
Resolve input coordinates to addresses and vice versa

/geocode/search
GET
Forward Geocode Service
navigate_next
lockQuery-ParameterAuthorization-Header
Returns a JSON formatted list of objects corresponding to the search input. boundary.*-parameters can be combined if they are overlapping. The interactivity for this enpoint is experimental! Please refer to this external Documentation

/geocode/autocomplete
GET
Geocode Autocomplete Service
navigate_next
lockQuery-ParameterAuthorization-Header
Requests should be throttled when using this endpoint!
Be aware that Responses are asynchronous.
Returns a JSON formatted list of objects corresponding to the search input. boundary.*-parameters can be combined if they are overlapping. The interactivity for this enpoint is experimental! Please refer to this external Documentation

/geocode/search/structured
GET
Structured Forward Geocode Service (beta)
navigate_next
lockQuery-ParameterAuthorization-Header
Returns a JSON formatted list of objects corresponding to the search input. The interactivity for this enpoint is experimental! Please refer to this external Documentation

/geocode/reverse
GET
Reverse Geocode Service
navigate_next
lockQuery-ParameterAuthorization-Header
Returns the next enclosing object with an address tag which surrounds the given coordinate. The interactivity for this enpoint is experimental! Please refer to this external Documentation