# Dataset Format

The native DatasetLint format is a local folder with JSON metadata and calibration plus CSV data files.

## Layout

```text
dataset/
  metadata.json
  calibration.json
  sensors/
    camera_front.csv
    imu.csv
    gps.csv
  labels/
    detections.csv
  trajectories/
    ego.csv
  images/
    000001.jpg
```

Only `metadata.json` and `calibration.json` are required files. Sensor, label, trajectory, and image files are validated when present or referenced.

## Metadata

```json
{
  "dataset_name": "sample_log",
  "version": "0.1",
  "sensors": ["camera_front", "imu", "gps"],
  "duration_sec": 0.2
}
```

Fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `dataset_name` | yes | Dataset identifier |
| `version` | recommended | Dataset version string |
| `sensors` | yes | Declared sensor names |
| `duration_sec` | recommended | Expected duration in seconds |

## Calibration

```json
{
  "camera_front": {
    "intrinsics": [[1000, 0, 640], [0, 1000, 360], [0, 0, 1]],
    "extrinsics": {
      "translation": [0.5, 0.0, 1.2],
      "rotation_quat": [1, 0, 0, 0]
    }
  }
}
```

Declared sensors should have calibration entries. Camera sensors need valid `intrinsics`. All calibration entries need `extrinsics.translation` with 3 numbers and `extrinsics.rotation_quat` with 4 normalized values.

## Sensor CSVs

Camera:

```csv
timestamp,path,width,height
0.0,images/000001.jpg,1280,720
```

`filename` is accepted as an alias for `path` when `path` is absent.

IMU:

```csv
timestamp,ax,ay,az,gx,gy,gz
0.0,0.0,0.0,9.8,0.0,0.0,0.0
```

GPS:

```csv
timestamp,lat,lon,alt
0.0,37.0,-122.0,10.0
```

Other sensors require at least:

```csv
timestamp
0.0
```

## Labels

Detection labels require:

```csv
timestamp,track_id,class,x,y,width,height,confidence
0.0,track-1,car,10,20,50,40,0.95
```

## Trajectories

Trajectories require:

```csv
timestamp,x,y,yaw,vx,vy
0.0,0.0,0.0,0.0,10.0,0.0
```

## Minimal Valid Example

Use `examples/minimal_dataset` as the complete working reference.
