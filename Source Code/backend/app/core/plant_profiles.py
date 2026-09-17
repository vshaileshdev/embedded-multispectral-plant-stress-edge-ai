PLANT_PROFILES = {
    "tomato": {
        "species": "Tomato",
        "scientific_name": "Solanum lycopersicum",
        "plant_id_prefix": "TOM",
        "profile_status": "Active",
        "model_status": "ML Model Available",
        "model_id": "Tomato Research Random Forest v1.0.0",
        "supported_stresses": ["Control", "Water Stress", "Nitrogen Deficit"],
        "sensor_profile": "VIS-NIR Research Spectrometer (832 band)",
        "can_diagnose": True
    },
    "spinach": {
        "species": "Spinach",
        "scientific_name": "Spinacia oleracea",
        "plant_id_prefix": "SPI",
        "profile_status": "Profile Ready",
        "model_status": "ML Model Pending Validation",
        "model_id": "None",
        "supported_stresses": ["Pending dataset/model validation"],
        "sensor_profile": "Pending",
        "can_diagnose": False
    },
    "chrysanthemum": {
        "species": "Chrysanthemum",
        "scientific_name": "Chrysanthemum morifolium",
        "plant_id_prefix": "CHR",
        "profile_status": "Profile Ready",
        "model_status": "ML Model Pending Validation",
        "model_id": "None",
        "supported_stresses": ["Nutrient-stress model pending validation"],
        "sensor_profile": "Pending",
        "can_diagnose": False
    },
    "peace_lily": {
        "species": "Peace Lily",
        "scientific_name": "Spathiphyllum",
        "plant_id_prefix": "PIL",
        "profile_status": "Profile Ready",
        "model_status": "ML Model Pending Validation",
        "model_id": "None",
        "supported_stresses": ["Plant-specific stress model pending validation"],
        "sensor_profile": "Pending",
        "can_diagnose": False
    }
}
