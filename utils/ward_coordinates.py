"""
Ward Coordinates and Geographic Metadata for ADES BIDAI
Provides centroid coordinates and bounding layouts for all 60 wards across:
- Dhaka North City Corporation (DNCC) - 20 wards
- Dhaka South City Corporation (DSCC) - 20 wards
- Chattogram City Corporation (CCC) - 10 wards
- Gazipur City Corporation (GCC) - 5 wards
- Narayanganj City Corporation (NCC) - 5 wards
"""

import math

# Centroid coordinates for Dhaka North (DNCC) - 20 wards
DNCC_COORDS = {
    "DNCC_Ward_01": (23.868, 90.398, "Uttara East"),
    "DNCC_Ward_02": (23.818, 90.364, "Mirpur-12"),
    "DNCC_Ward_03": (23.812, 90.370, "Mirpur-11"),
    "DNCC_Ward_04": (23.805, 90.374, "Mirpur-13"),
    "DNCC_Ward_05": (23.808, 90.360, "Mirpur-6"),
    "DNCC_Ward_06": (23.802, 90.365, "Mirpur-7"),
    "DNCC_Ward_07": (23.806, 90.354, "Mirpur-2"),
    "DNCC_Ward_08": (23.798, 90.352, "Mirpur-1"),
    "DNCC_Ward_09": (23.788, 90.350, "Kallyanpur"),
    "DNCC_Ward_10": (23.792, 90.340, "Gabtoli"),
    "DNCC_Ward_11": (23.784, 90.358, "Paikpara"),
    "DNCC_Ward_12": (23.782, 90.364, "Shah Ali"),
    "DNCC_Ward_13": (23.792, 90.375, "Kafrul"),
    "DNCC_Ward_14": (23.785, 90.380, "Shewrapara"),
    "DNCC_Ward_15": (23.825, 90.385, "Cantonment"),
    "DNCC_Ward_16": (23.790, 90.390, "Mohakhali"),
    "DNCC_Ward_17": (23.830, 90.418, "Khilkhet"),
    "DNCC_Ward_18": (23.840, 90.425, "Kuril"),
    "DNCC_Ward_19": (23.795, 90.415, "Banani"),
    "DNCC_Ward_20": (23.788, 90.418, "Gulshan-1"),
}

# Centroid coordinates for Dhaka South (DSCC) - 20 wards
DSCC_COORDS = {
    "DSCC_Ward_01": (23.750, 90.428, "Khilgaon"),
    "DSCC_Ward_02": (23.742, 90.425, "Bashabo"),
    "DSCC_Ward_03": (23.748, 90.435, "Madartek"),
    "DSCC_Ward_04": (23.738, 90.430, "Mugdha"),
    "DSCC_Ward_05": (23.745, 90.405, "Shantinagar"),
    "DSCC_Ward_06": (23.732, 90.408, "Motijheel"),
    "DSCC_Ward_07": (23.725, 90.415, "Wari"),
    "DSCC_Ward_08": (23.720, 90.420, "Sutrapur"),
    "DSCC_Ward_09": (23.715, 90.408, "Armanitola"),
    "DSCC_Ward_10": (23.712, 90.400, "Lalbagh"),
    "DSCC_Ward_11": (23.730, 90.385, "Dhanmondi"),
    "DSCC_Ward_12": (23.740, 90.375, "Jigatola"),
    "DSCC_Ward_13": (23.745, 90.365, "Hazaribagh"),
    "DSCC_Ward_14": (23.735, 90.395, "New Market"),
    "DSCC_Ward_15": (23.728, 90.398, "Azimpur"),
    "DSCC_Ward_16": (23.718, 90.380, "Kamrangirchar North"),
    "DSCC_Ward_17": (23.710, 90.375, "Kamrangirchar South"),
    "DSCC_Ward_18": (23.695, 90.435, "Postogola"),
    "DSCC_Ward_19": (23.705, 90.430, "Jatrabari"),
    "DSCC_Ward_20": (23.715, 90.425, "Sayedabad"),
}

# Centroid coordinates for Chattogram (CCC) - 10 wards
CCC_COORDS = {
    "CCC_Ward_01": (22.385, 91.805, "Pahartali"),
    "CCC_Ward_02": (22.378, 91.815, "Jalalabad"),
    "CCC_Ward_03": (22.370, 91.825, "Panchlaish"),
    "CCC_Ward_04": (22.365, 91.835, "Chandgaon"),
    "CCC_Ward_05": (22.358, 91.840, "Mohra"),
    "CCC_Ward_06": (22.352, 91.830, "Bakalia"),
    "CCC_Ward_07": (22.345, 91.820, "Kotwali"),
    "CCC_Ward_08": (22.340, 91.810, "Anderkilla"),
    "CCC_Ward_09": (22.335, 91.800, "Agrabad"),
    "CCC_Ward_10": (22.325, 91.790, "Halishahar"),
}

# Centroid coordinates for Gazipur (GCC) - 5 wards
GCC_COORDS = {
    f"GCC_Ward_{i:02d}": (round(23.985 + (i * 0.012), 4), round(90.380 + ((i % 3) * 0.015), 4), f"Gazipur Sector {i}")
    for i in range(1, 6)
}

# Centroid coordinates for Narayanganj (NCC) - 5 wards
NCC_COORDS = {
    f"NCC_Ward_{i:02d}": (round(23.615 + (i * 0.010), 4), round(90.490 + ((i % 2) * 0.012), 4), f"Narayanganj Zone {i}")
    for i in range(1, 6)
}

# Unified 60-Ward coordinates map
ALL_WARD_COORDS = {
    **DNCC_COORDS,
    **DSCC_COORDS,
    **CCC_COORDS,
    **GCC_COORDS,
    **NCC_COORDS
}

# Ward geographical area in square kilometers for all 60 wards
WARD_AREAS = {
    # DNCC (20 wards)
    "DNCC_Ward_01": 4.2, "DNCC_Ward_02": 3.1, "DNCC_Ward_03": 2.8, "DNCC_Ward_04": 2.5,
    "DNCC_Ward_05": 2.6, "DNCC_Ward_06": 3.4, "DNCC_Ward_07": 2.9, "DNCC_Ward_08": 3.0,
    "DNCC_Ward_09": 2.4, "DNCC_Ward_10": 3.8, "DNCC_Ward_11": 2.2, "DNCC_Ward_12": 2.1,
    "DNCC_Ward_13": 3.5, "DNCC_Ward_14": 2.7, "DNCC_Ward_15": 5.2, "DNCC_Ward_16": 2.3,
    "DNCC_Ward_17": 4.1, "DNCC_Ward_18": 3.6, "DNCC_Ward_19": 3.2, "DNCC_Ward_20": 3.5,
    # DSCC (20 wards)
    "DSCC_Ward_01": 2.2, "DSCC_Ward_02": 1.9, "DSCC_Ward_03": 2.1, "DSCC_Ward_04": 1.8,
    "DSCC_Ward_05": 1.7, "DSCC_Ward_06": 1.5, "DSCC_Ward_07": 1.4, "DSCC_Ward_08": 1.6,
    "DSCC_Ward_09": 1.3, "DSCC_Ward_10": 1.4, "DSCC_Ward_11": 2.6, "DSCC_Ward_12": 2.0,
    "DSCC_Ward_13": 2.3, "DSCC_Ward_14": 1.8, "DSCC_Ward_15": 1.7, "DSCC_Ward_16": 2.2,
    "DSCC_Ward_17": 1.9, "DSCC_Ward_18": 1.6, "DSCC_Ward_19": 2.4, "DSCC_Ward_20": 1.8,
    # CCC (10 wards)
    "CCC_Ward_01": 4.8, "CCC_Ward_02": 3.9, "CCC_Ward_03": 3.5, "CCC_Ward_04": 4.1,
    "CCC_Ward_05": 5.2, "CCC_Ward_06": 3.2, "CCC_Ward_07": 2.6, "CCC_Ward_08": 2.4,
    "CCC_Ward_09": 3.7, "CCC_Ward_10": 4.5,
    # GCC (5 wards)
    "GCC_Ward_01": 5.5, "GCC_Ward_02": 4.8, "GCC_Ward_03": 5.1, "GCC_Ward_04": 6.2, "GCC_Ward_05": 5.9,
    # NCC (5 wards)
    "NCC_Ward_01": 3.4, "NCC_Ward_02": 4.2, "NCC_Ward_03": 3.8, "NCC_Ward_04": 3.1, "NCC_Ward_05": 3.6,
}


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes Great-Circle Haversine distance in kilometers between two geo-coordinates.
    """
    if None in (lat1, lon1, lat2, lon2):
        return 999.0
    r = 6371.0  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2) ** 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return round(r * c, 2)


def get_ward_geo_dataframe(predictions_df):
    """
    Augments predictions DataFrame with latitude, longitude, and locality names.
    """
    df = predictions_df.copy()
    lats = []
    lons = []
    localities = []

    for ward in df["ward_id"]:
        if ward in ALL_WARD_COORDS:
            lat, lon, loc = ALL_WARD_COORDS[ward]
            lats.append(lat)
            lons.append(lon)
            localities.append(loc)
        else:
            # Fallback Dhaka center
            lats.append(23.8103)
            lons.append(90.4125)
            localities.append("Urban Zone")

    df["lat"] = lats
    df["lon"] = lons
    df["locality"] = localities
    return df
