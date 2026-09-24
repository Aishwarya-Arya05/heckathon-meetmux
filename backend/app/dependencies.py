"""
Dependency injection for FastAPI.

Provides service instances to route handlers via FastAPI's Depends() system.
Services are created during app lifespan and stored in app.state.
"""

from __future__ import annotations

from fastapi import Depends, Request

from app.services.feature_builder import FeatureBuilder
from app.services.graph_service import GraphServiceBase
from app.services.prediction_service import PredictionServiceBase
from app.services.route_service import RouteServiceBase


def get_graph_service(request: Request) -> GraphServiceBase:
    return request.app.state.graph_service


def get_route_service(request: Request) -> RouteServiceBase:
    return request.app.state.route_service


def get_prediction_service(request: Request) -> PredictionServiceBase:
    return request.app.state.prediction_service


def get_feature_builder(request: Request) -> FeatureBuilder:
    return request.app.state.feature_builder
