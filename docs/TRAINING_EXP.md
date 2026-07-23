# YOLOv26 Nano Person Intrusion Detection

## Overview

This experiment trains a YOLOv26 nano model on a person-only COCO-format dataset and performs a separate final evaluation on the **test** split after training.

## Key Metrics

| Metric | Value |
|---|---:|
| Precision | 0.7886 |
| Recall | 0.6226 |
| mAP@50 | 0.7352 |
| mAP@50-95 | 0.5013 |
| Test images | 1,452 |
| Test instances | 6,367 |

## Dataset

| Split | Images | Notes |
|---|---:|---|
| Train | 64,892 | 126 background images, 0 corrupt files during scan |
| Validation | 1,437 | Used for in-training validation |
| Test | 1,452 | Used for final post-training evaluation |

- Target class: `person`
- COCO class filter: `classes: [0]`
- Mode: object detection

## Model

- Model family: **YOLO26n**
- Layers: **260**
- Parameters: **2,504,190**
- GFLOPs: **5.8**
- Starting weights: `../weights/yolo26n.pt`

## Training Configuration

| Setting | Value |
|---|---|
| Epochs | 115 |
| Patience | 10 |
| Image size | 640 |
| Batch size | 128 |
| Optimizer | `auto` |
| Workers | 8 |
| Devices | `0,1` |
| Mixed precision | AMP enabled |
| Half precision | Enabled |
| Deterministic | True |
| Max detections | 400 |
| Classification loss gain | 0.1 |

### Augmentations

- `hsv_h=0.015`
- `hsv_s=0.5`
- `hsv_v=0.3`
- `degrees=5.0`
- `translate=0.1`
- `scale=0.3`
- `fliplr=0.5`
- `mosaic=0.1`
- `close_mosaic=15`
- `copy_paste=0.0`
- `mixup=0.0`
- `cutmix=0.0`

## Environment

| Component | Value |
|---|---|
| Framework | Ultralytics 8.4.49 |
| Python | 3.11.11 |
| PyTorch | 2.6.0+cu118 |
| GPUs | 2 × Tesla P100-PCIE-16GB |
| GPU memory per device | 16,276 MiB |

## Evaluation Speed

| Stage | Time per image |
|---|---:|
| Preprocess | 0.7 ms |
| Inference | 2.1 ms |
| Loss | 0.0 ms |
| Postprocess | 0.1 ms |

## Notes on Results

- Final metrics shown above are **test-set** metrics.
- Validation snapshots during training were slightly higher in some checkpoints, but the final reported result is the held-out test evaluation.
- A distributed training failure appears earlier in the log, but the run later continues and produces final test results successfully.

## Reproducing the Run

```bash
python train.py -c config.yaml
```

### Expected Files

- `config.yaml` — pipeline configuration
- `train.py` — training and test evaluation entry point
- `../weights/yolo26n.pt` — pretrained starting weights
- `../datasets/coco_local/data.yaml` — dataset definition

## Intended Use

This model is intended for **person detection in intrusion-detection workflows**, including perimeter monitoring, restricted-zone surveillance, and human-presence alerting in safety or security pipelines.

## Limitations

- This experiment is person-only and does not model multi-class threats.
- Recall remains lower than precision, so missed detections may still occur in difficult scenes.
- No billing logs were available, so exact monetary compute cost is not reported.