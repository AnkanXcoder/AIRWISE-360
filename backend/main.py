import os


from datetime import date, datetime, timezone



from fastapi import FastAPI, HTTPException, Query

from fastapi.middleware.cors import CORSMiddleware



# Database
from backend.database import (

          initialize_database,

          get_historical_measurements,

          get_measurement_count

)



# Services
from backend.services.forecast_service import forecast_service

from backend.services.ml_readiness_service import ml_readiness_service

from backend.services.openaq_service import openaq_service

from backend.services.data_quality import process_measurements

from backend.services.collection_service import collect_station_data

from backend.services.city_comparison_service import city_comparison_service

from backend.services.analytics_service import analytics_service

from backend.services.event_service import event_service

from backend.services.diwali_service import diwali_impact_service

from backend.services.health_service import health_service

from backend.services.exposure_service import exposure_service

from backend.services.india_registry_service import india_registry_service

from backend.services.india_station_service import india_station_service

from backend.services.cpcb_aqi_service import calculate_cpcb_aqi
from backend.services.historical_ingestion_service import ingest_station_historical_data



# ==================================================
# APPLICATION CONFIGURATION
# ==================================================
app = FastAPI(

          title="AIRWISE 360° API",

          description="Air Quality Intelligence & Decision Support System",

          version="1.2.0"

)





app.add_middleware(

          CORSMiddleware,

          allow_origins=[
                    origin.strip()
                    for origin in os.getenv(
                        "AIRWISE_CORS_ORIGINS",
                        "http://localhost:5173,http://localhost:5174"
                    ).split(",")
                    if origin.strip()
          ],

          allow_credentials=True,

          allow_methods=["*"],

          allow_headers=["*"],

)





# ==================================================
# STATION CONFIGURATION
# ==================================================
STATIONS = {

          6950: {

                    "name": "Jadavpur",

                    "city": "Kolkata",

                    "state": "West Bengal",

                    "latitude": 22.49929,

                    "longitude": 88.36917

          }

}





VALID_POLLUTANTS = {

          "pm25",

          "pm10",

          "no2",

          "so2",

          "co",

          "o3",

          "nh3",

          "pb"

}





# ==================================================
# STARTUP
# ==================================================
@app.on_event("startup")

def startup():

          initialize_database()





# ==================================================
# HOME
# ==================================================
@app.get("/")

def home():

          return {

                    "project": "AIRWISE 360°",

                    "status": "running",

                    "version": "1.2.0",

                    "message": "Air Quality Intelligence API is operational"

          }





# ==================================================
# STATION APIs
# ==================================================
@app.get("/api/stations")

def get_stations():



          return {

                    "count": len(STATIONS),

                    "stations": [

                              {

                                        "station_id": station_id,

                                        **station

                              }

                              for station_id, station in STATIONS.items()

                    ]

          }





@app.get("/api/stations/{location_id}/measurements")

def get_station_measurements(location_id: int):



          try:

                    records = openaq_service.get_station_measurements(

                              location_id

                    )



                    if not records:

                              raise HTTPException(

                                        status_code=404,

                                        detail="No sensor measurements found"

                              )



                    quality_result = process_measurements(records)



                    station = STATIONS.get(location_id)



                    return {

                              "project": "AIRWISE 360°",

                              "source": "OpenAQ",

                              "data_type": "ground_sensor_observations",

                              "station_id": location_id,

                              "station": station,

                              "retrieved_at": datetime.now(timezone.utc).isoformat(),

                              "summary": quality_result["summary"],

                              "pollutants": quality_result["selected_pollutants"],

                              "all_sensor_records": quality_result["records"]

                    }



          except HTTPException:

                    raise



          except (RuntimeError, ValueError) as error:

                    raise HTTPException(

                              status_code=502,

                              detail=str(error)

                    )



          except Exception:

                    raise HTTPException(

                              status_code=500,

                              detail="Unexpected server error"

                    )





@app.post("/api/stations/{location_id}/collect")

def collect_station(location_id: int):



          station = STATIONS.get(location_id)



          if not station:

                    raise HTTPException(

                              status_code=404,

                              detail="Station is not registered in AIRWISE"

                    )



          try:

                    result = collect_station_data(

                              location_id=location_id,

                              station_name=station["name"]

                    )



                    return {

                              "status": "success",

                              "collection": result,

                              "database_total_records": get_measurement_count()

                    }



          except (RuntimeError, ValueError) as error:

                    raise HTTPException(

                              status_code=502,

                              detail=str(error)

                    )



          except Exception:

                    raise HTTPException(

                              status_code=500,

                              detail="Data collection failed"

                    )





@app.get("/api/stations/{location_id}/history")

def get_station_history(

          location_id: int,

          pollutant: str = Query(...),

          limit: int = Query(100, ge=1, le=1000)

):



          pollutant = pollutant.lower()



          if pollutant not in VALID_POLLUTANTS:

                    raise HTTPException(

                              status_code=400,

                              detail=f"Unsupported pollutant. Choose from {sorted(VALID_POLLUTANTS)}"

                    )



          if location_id not in STATIONS:

                    raise HTTPException(

                              status_code=404,

                              detail="Station not registered"

                    )



          try:

                    records = get_historical_measurements(

                              location_id=location_id,

                              pollutant=pollutant,

                              limit=limit

                    )



                    # Database returns newest first.
                    # Charts need chronological order.
                    records.reverse()



                    return {

                              "station_id": location_id,

                              "station": STATIONS[location_id],

                              "pollutant": pollutant,

                              "record_count": len(records),

                              "data_type": "stored_sensor_observations",

                              "records": records

                    }



          except Exception:

                    raise HTTPException(

                              status_code=500,

                              detail="Unable to retrieve historical data"

                    )





@app.get("/api/stations/{location_id}/quality")

def get_station_quality(location_id: int):



          if location_id not in STATIONS:

                    raise HTTPException(

                              status_code=404,

                              detail="Station not registered"

                    )



          try:

                    records = openaq_service.get_station_measurements(

                              location_id

                    )



                    if not records:

                              raise HTTPException(

                                        status_code=404,

                                        detail="No measurements available for quality analysis"

                              )



                    result = process_measurements(records)



                    return {

                              "station_id": location_id,

                              "station": STATIONS[location_id],

                              "source": "OpenAQ",

                              "assessed_at": datetime.now(timezone.utc).isoformat(),

                              "quality_summary": result["summary"]

                    }



          except HTTPException:

                    raise



          except Exception:

                    raise HTTPException(

                              status_code=502,

                              detail="Unable to assess data quality"

                    )





# ==================================================
# AIR QUALITY FORECAST
# ==================================================
@app.get("/api/forecast")

def get_air_quality_forecast(

          latitude: float = Query(22.49929, ge=-90, le=90),

          longitude: float = Query(88.36917, ge=-180, le=180)

):



          try:

                    result = forecast_service.get_forecast(

                              latitude=latitude,

                              longitude=longitude

                    )



                    return {

                              "project": "AIRWISE 360°",

                              "source": result["source"],

                              "data_type": result["data_type"],

                              "model": result["model"],

                              "location": result["location"],

                              "units": result["units"],

                              "forecast": result["hourly"]

                    }



          except RuntimeError as error:

                    raise HTTPException(

                              status_code=502,

                              detail=str(error)

                    )



          except Exception:

                    raise HTTPException(

                              status_code=500,

                              detail="Unable to retrieve air quality forecast"

                    )





# ==================================================
# CITY COMPARISON
# ==================================================
@app.get("/api/cities/compare")

def compare_cities():



          try:

                    return city_comparison_service.compare_cities()



          except RuntimeError as error:

                    raise HTTPException(

                              status_code=502,

                              detail=str(error)

                    )



          except Exception:

                    raise HTTPException(

                              status_code=500,

                              detail="City comparison failed"

                    )





# ==================================================
# HISTORICAL ANALYTICS
# ==================================================
@app.get("/api/analytics/{location_id}/history")

def get_station_analytics(

          location_id: int,

          pollutant: str = "pm25",

          limit: int = Query(100, ge=1, le=10000)

):



          pollutant = pollutant.lower()



          if pollutant not in VALID_POLLUTANTS:

                    raise HTTPException(

                              status_code=400,

                              detail="Unsupported pollutant"

                    )



          try:

                    measurements = get_historical_measurements(

                              location_id,

                              pollutant,

                              limit

                    )



                    return {

                              "location_id": location_id,

                              "pollutant": pollutant,

                              "analytics": analytics_service.analyze_history(

                                        measurements

                              )

                    }



          except Exception as error:

                    raise HTTPException(

                              status_code=500,

                              detail=f"Historical analytics failed: {str(error)}"

                    )





# ==================================================
# POLLUTION SPIKE DETECTION
# ==================================================
@app.get("/api/analytics/{location_id}/spikes")

def get_station_spikes(

          location_id: int,

          pollutant: str = "pm25",

          limit: int = Query(100, ge=1, le=10000)

):



          pollutant = pollutant.lower()



          if pollutant not in VALID_POLLUTANTS:

                    raise HTTPException(

                              status_code=400,

                              detail="Unsupported pollutant"

                    )



          try:

                    measurements = get_historical_measurements(

                              location_id,

                              pollutant,

                              limit

                    )



                    analytics = analytics_service.analyze_history(

                              measurements

                    )



                    return {

                              "location_id": location_id,

                              "pollutant": pollutant,

                              "sensor_analysis": analytics.get(

                                        "sensor_analysis",

                                        {}

                              )

                    }



          except Exception as error:

                    raise HTTPException(

                              status_code=500,

                              detail=f"Spike detection failed: {str(error)}"

                    )





# ==================================================
# FLATLINE DETECTION
# ==================================================
@app.get("/api/analytics/{location_id}/flatlines")

def get_station_flatlines(

          location_id: int,

          pollutant: str = "pm25",

          limit: int = Query(100, ge=1, le=10000)

):



          pollutant = pollutant.lower()



          if pollutant not in VALID_POLLUTANTS:

                    raise HTTPException(

                              status_code=400,

                              detail="Unsupported pollutant"

                    )



          try:

                    measurements = get_historical_measurements(

                              location_id,

                              pollutant,

                              limit

                    )



                    analytics = analytics_service.analyze_history(

                              measurements

                    )



                    flatlines = {}



                    for sensor_id, result in analytics.get(

                              "sensor_analysis",

                              {}

                    ).items():



                              detection = result["spike_detection"]



                              flatlines[sensor_id] = {

                                        "flatline_detected": detection.get(

                                                  "flatline_detected",

                                                  False

                                        ),

                                        "longest_flatline": detection.get(

                                                  "longest_flatline",

                                                  0

                                        ),

                                        "status": detection["status"]

                              }



                    return {

                              "location_id": location_id,

                              "pollutant": pollutant,

                              "flatline_analysis": flatlines

                    }



          except Exception as error:

                    raise HTTPException(

                              status_code=500,

                              detail=f"Flatline detection failed: {str(error)}"

                    )





# ==================================================
# POLLUTION EVENT LIFECYCLE API
# ==================================================
@app.get("/api/analytics/{location_id}/events")

def get_pollution_events(

          location_id: int,

          pollutant: str = "pm25"

):



          pollutant = pollutant.lower()



          if pollutant not in VALID_POLLUTANTS:

                    raise HTTPException(

                              status_code=400,

                              detail="Unsupported pollutant"

                    )



          try:

                    return event_service.get_event_report(

                              location_id=location_id,

                              pollutant=pollutant

                    )



          except ValueError as error:

                    raise HTTPException(

                              status_code=400,

                              detail=str(error)

                    )



          except RuntimeError as error:

                    raise HTTPException(

                              status_code=502,

                              detail=str(error)

                    )



          except Exception:

                    raise HTTPException(

                              status_code=500,

                              detail="Pollution event analysis failed."

                    )





# ==================================================
# DIWALI IMPACT ANALYTICS
# ==================================================
@app.get("/api/analytics/diwali")

def get_diwali_impact(

          diwali_start: date,

          diwali_end: date,

          pollutant: str = "pm25",

          pre_days: int = Query(7, ge=1, le=30),

          post_days: int = Query(7, ge=1, le=30),

          min_records: int = Query(3, ge=1),

          min_days: int = Query(2, ge=1),

          kolkata_location_id: int = 6950,

          delhi_location_id: int | None = None

):



          try:

                    city_locations = {

                              "Kolkata": kolkata_location_id,

                              "Delhi": delhi_location_id

                    }



                    return diwali_impact_service.generate_report(

                              diwali_start=diwali_start,

                              diwali_end=diwali_end,

                              pollutant=pollutant,

                              pre_days=pre_days,

                              post_days=post_days,

                              min_records=min_records,

                              min_days=min_days,

                              city_locations=city_locations

                    )



          except ValueError as error:

                    raise HTTPException(

                              status_code=400,

                              detail=str(error)

                    )



          except Exception:

                    raise HTTPException(

                              status_code=500,

                              detail="Diwali impact report generation failed."

                    )





# ==================================================
# HEALTH GUIDANCE
# ==================================================
@app.get("/api/health/guidance")

def get_health_guidance(

          official_aqi: int | None = None,

          source_type: str = "unknown",

          sensitive_group: bool = False,

          symptoms: bool = False

):



          try:

                    return health_service.generate_guidance(

                              official_aqi=official_aqi,

                              source_type=source_type,

                              sensitive_group=sensitive_group,

                              symptoms=symptoms

                    )



          except ValueError as error:

                    raise HTTPException(

                              status_code=400,

                              detail=str(error)

                    )



          except Exception:

                    raise HTTPException(

                              status_code=500,

                              detail="Health guidance generation failed."

                    )





# ==================================================
# PERSONAL EXPOSURE RECOMMENDATION
# ==================================================
@app.get("/api/exposure/recommend")

def recommend_exposure_window(

          activity: str = "walking",

          duration_minutes: int = Query(30, ge=1, le=1440),

          sensitive_group: bool = False,

          latitude: float = Query(22.49929, ge=-90, le=90),

          longitude: float = Query(88.36917, ge=-180, le=180),

          pollutant: str = "pm25",

          window_hours: int = Query(3, ge=1, le=24)

):



          try:

                    return exposure_service.calculate_exposure(

                              activity=activity,

                              duration_minutes=duration_minutes,

                              sensitive_group=sensitive_group,

                              latitude=latitude,

                              longitude=longitude,

                              pollutant=pollutant,

                              window_hours=window_hours

                    )



          except ValueError as error:

                    raise HTTPException(

                              status_code=400,

                              detail=str(error)

                    )



          except Exception:

                    raise HTTPException(

                              status_code=502,

                              detail="Exposure recommendation failed."

                    )





# ==================================================
# ML DATASET READINESS
# ==================================================
@app.get("/api/ml/readiness/{location_id}")
def check_ml_readiness(
    location_id: int,
    pollutant: str = Query("pm25"),
    limit: int = Query(10000, ge=1, le=50000)
):
    pollutant = pollutant.lower()

    if pollutant not in VALID_POLLUTANTS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported pollutant"
        )

    try:
        # 1. Assess historical data readiness.
        records = get_historical_measurements(
            location_id=location_id,
            pollutant=pollutant,
            limit=limit
        )

        historical_result = (
            ml_readiness_service.assess_readiness(records)
        )

        # 2. Assess forecasting readiness only where the
        # current forecasting pipeline is configured.
        if location_id == 6950 and pollutant == "pm25":
            forecasting_result = (
                ml_readiness_service.assess_forecasting_readiness()
            )
        else:
            forecasting_result = {
                "status": "unsupported",
                "ready": False,
                "production_ready": False,
                "message": (
                    "Forecasting assessment is not configured "
                    "for this location and pollutant."
                )
            }

        # 3. Return legacy fields plus both detailed assessments.
        return {
            "project": "AIRWISE 360°",
            "location_id": location_id,
            "pollutant": pollutant,
            "data_source": "AIRWISE SQLite historical observations",
            **historical_result,
            "historical_readiness": historical_result,
            "forecasting_readiness": forecasting_result
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="ML readiness assessment failed."
        )


# ==================================================
# AIRWISE INDIA-WIDE STATION APIs
# ==================================================
@app.get("/api/india/stations/{source}/{source_location_id}/measurements")
def get_india_station_measurements(source: str, source_location_id: int):
    """Fetch observations for any station in the India registry.

    The source is part of the key because location IDs are not globally unique.
    """
    station = india_registry_service.get_station(source, source_location_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station is not present in the India registry.")

    if source.lower() != "openaq":
        raise HTTPException(
            status_code=501,
            detail=f"Live measurement retrieval is not configured for source '{source}'. The station remains registered, but readings are unavailable."
        )

    try:
        records = openaq_service.get_station_measurements(source_location_id)
        if not records:
            raise HTTPException(status_code=404, detail="No sensor measurements are currently available for this station.")

        quality_result = process_measurements(records)
        return {
            "project": "AIRWISE 360°",
            "source": "OpenAQ",
            "data_type": "ground_sensor_observations",
            "station_id": source_location_id,
            "station": {
                "name": station.get("station_name"),
                "locality": station.get("locality"),
                "city": station.get("city"),
                "district": station.get("district"),
                "state": station.get("state"),
                "latitude": station.get("latitude"),
                "longitude": station.get("longitude")
            },
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "summary": quality_result["summary"],
            "pollutants": quality_result["selected_pollutants"],
            "all_sensor_records": quality_result["records"]
        }
    except HTTPException:
        raise
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=502, detail=str(error))
    except Exception:
        raise HTTPException(status_code=502, detail="Unable to retrieve station observations from the source.")


@app.post("/api/india/discover")
def discover_india_locations(
    limit: int = Query(1000, ge=1, le=1000),
    max_pages: int = Query(100, ge=1, le=100)
):
    """
    Discover Indian air-quality monitoring locations from OpenAQ
    and upsert them into the AIRWISE India registry.

    Station identity is source-scoped:
    (source, source_location_id).
    """

    if not india_station_service.api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAQ_API_KEY is missing from the backend .env file."
        )

    try:
        # 1. Discover locations from OpenAQ.
        discovery = india_station_service.discover_india_stations(
            limit=limit,
            max_pages=max_pages
        )

        stations = discovery.get("stations", [])

        if not stations:
            return {
                "status": "success",
                "message": "No additional Indian locations were returned by OpenAQ.",
                "discovered_locations": 0,
                "upserted_records": 0,
                "coverage": india_registry_service.get_summary()
            }

        # 2. Save or update records in the national registry.
        upserted_records = india_registry_service.save_stations(
            stations
        )

        # 3. Read updated national coverage.
        summary = india_registry_service.get_summary()
        filters = india_registry_service.get_geographic_filters()

        return {
            "status": "success",
            "country": "India",
            "source": "OpenAQ",
            "pages_fetched": discovery.get("pages_fetched", 0),
            "discovered_locations": discovery.get(
                "total_locations_discovered", 0
            ),
            "geolocated_locations": discovery.get(
                "geolocated_locations", 0
            ),
            "upserted_records": upserted_records,
            "coverage": {
                **summary,
                "states_available": len(filters["states"]),
                "districts_available": len(filters["districts"]),
                "cities_available": len(filters["cities"])
            },
            "message": (
                "Indian location discovery completed. "
                "The registry has been updated."
            )
        }

    except HTTPException:
        raise

    except (RuntimeError, ValueError) as error:
        raise HTTPException(
            status_code=502,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"India location discovery failed: {error}"
        )


@app.get("/api/india/overview")

def india_overview():



          summary = india_registry_service.get_summary()



          filters = india_registry_service.get_geographic_filters()



          return {

                    "status": "success",

                    "country": "India",

                    "data_source": "OpenAQ",

                    "total_locations": summary["total_locations"],

                    "geolocated_locations": summary["geolocated_locations"],

                    "monitor_locations": summary["monitor_locations"],

                    "mobile_locations": summary["mobile_locations"],

                    "states_available": len(filters["states"]),

                    "cities_available": len(filters["cities"]),

                    "districts_available": len(filters.get("districts", [])),

                    "locations_with_verified_city": summary.get("locations_with_city", 0),

                    "locations_with_district": summary.get("locations_with_district", 0),

                    "location_fallback_policy": "verified_city_then_district_and_state",

                    "geographic_metadata_status": (

                              "available"

                              if filters["states"] or filters["cities"]

                              else "pending_enrichment"

                    )

          }





@app.get("/api/india/stations")

def india_stations(

          page: int = Query(1, ge=1),

          limit: int = Query(100, ge=1, le=1000),

          search: str | None = None,

          state: str | None = None,

          city: str | None = None,

          district: str | None = None

):



          try:

                    return india_registry_service.get_stations(

                              page=page,

                              limit=limit,

                              search=search,

                              state=state,

                              city=city,

                              district=district

                    )



          except ValueError as error:

                    raise HTTPException(

                              status_code=400,

                              detail=str(error)

                    )



          except Exception:

                    raise HTTPException(

                              status_code=500,

                              detail="Unable to retrieve Indian monitoring locations."

                    )





@app.get("/api/india/filters")

def india_filters():



          return india_registry_service.get_geographic_filters()





@app.get("/api/india/map")

def india_map(

          limit: int = Query(1000, ge=1, le=10000)

):



          try:

                    return india_registry_service.get_map_stations(

                              limit=limit

                    )



          except ValueError as error:

                    raise HTTPException(

                              status_code=400,

                              detail=str(error)

                    )



          except Exception:

                    raise HTTPException(

                              status_code=500,

                              detail="Unable to retrieve map locations."

                    )

# ==================================================
# INDIA-WIDE OPENAQ HISTORICAL INGESTION
# ==================================================
@app.post("/api/india/stations/{source}/{source_location_id}/ingest")
def ingest_india_station_history(
    source: str,
    source_location_id: int,
    hours: int = Query(36, ge=24, le=168),
):
    """Fetch and persist historical observations for a registered OpenAQ station."""
    if source.lower() != "openaq":
        raise HTTPException(
            status_code=501,
            detail="Historical ingestion is currently supported for OpenAQ stations only.",
        )

    station = india_registry_service.get_station(source, source_location_id)
    if not station:
        raise HTTPException(
            status_code=404,
            detail="Station is not present in the India station registry.",
        )

    try:
        result = ingest_station_historical_data(
            location_id=source_location_id,
            station_name=station.get("station_name") or "Unknown station",
            hours=hours,
        )
        return {
            "project": "AIRWISE 360°",
            "source": "OpenAQ",
            "station_id": source_location_id,
            "station_name": station.get("station_name"),
            **result,
        }
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Historical ingestion failed: {error}",
        )


# ==================================================
# CPCB-METHODOLOGY AQI FOR INDIA-WIDE STATIONS
# ==================================================
@app.get("/api/india/stations/{source}/{source_location_id}/aqi")
def get_india_station_cpcb_aqi(source: str, source_location_id: int):
    """
    Calculate a CPCB-methodology AQI from historical observations
    already stored in AIRWISE SQLite for the selected station.

    This endpoint does not fetch or manufacture historical data.
    If the database lacks sufficient valid hourly observations, the
    calculation service returns INS UFFICIENT_DATA status.
    """
    station = india_registry_service.get_station(source, source_location_id)
    if not station:
        raise HTTPException(
            status_code=404,
            detail="Station is not present in the India registry."
        )

    if source.lower() != "openaq":
        raise HTTPException(
            status_code=501,
            detail=f"CPCB-methodology calculation is not configured for source '{source}'."
        )

    pollutants = ("pm25", "pm10", "no2", "so2", "co", "o3", "nh3", "pb")
    historical_records = []

    try:
        for pollutant in pollutants:
            rows = get_historical_measurements(
                location_id=source_location_id,
                pollutant=pollutant,
                limit=5000
            )
            historical_records.extend(rows)

        result = calculate_cpcb_aqi(historical_records)

        return {
            "project": "AIRWISE 360°",
            "source": "OpenAQ",
            "data_type": "historical_sensor_observations",
            "station_id": source_location_id,
            "station": {
                "name": station.get("station_name"),
                "locality": station.get("locality"),
                "city": station.get("city"),
                "district": station.get("district"),
                "state": station.get("state"),
                "latitude": station.get("latitude"),
                "longitude": station.get("longitude")
            },
            "historical_records_used": len(historical_records),
            **result
        }

    except HTTPException:
        raise
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"CPCB AQI calculation failed: {error}"
        )

