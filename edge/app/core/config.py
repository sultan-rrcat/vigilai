import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class EdgeSettings(BaseSettings):
    LOG_DIR: str = "./app/logs"
    CAMERA_ID: str = Field(..., validation_alias="CAMERA_ID")
    RTSP_URL: str = Field(..., validation_alias="RTSP_URL")
    FRAME_STRIDE: int = Field(default=3, validation_alias="FRAME_STRIDE")
    MODEL_PATH: str = Field(
        default="models/yolo26n_coco_local_1.onnx", validation_alias="MODEL_PATH"
    )
    KAFKA_BROKER: str = Field(..., validation_alias="KAFKA_BROKER")
    CENTRAL_API_URL: str = Field(..., validation_alias="CENTRAL_API_URL")

    # State Machine Thresholds
    MIN_DWELL_SECONDS: float = Field(default=2.0, validation_alias="MIN_DWELL_SECONDS")
    TRACK_TTL_SECONDS: float = Field(default=5.0, validation_alias="TRACK_TTL_SECONDS")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = EdgeSettings()
