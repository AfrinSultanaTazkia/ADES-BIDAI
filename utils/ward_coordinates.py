"""
Ward Coordinates and Geographic Metadata for ADES BIDAI
Provides centroid coordinates and bounding layouts for 60 wards across:
- Dhaka North City Corporation (DNCC) - 20 wards
- Dhaka South City Corporation (DSCC) - 15 wards
- Chattogram City Corporation (CCC) - 10 wards
- Gazipur City Corporation (GCC) - 8 wards
- Narayanganj City Corporation (NCC) - 7 wards
"""

# Centroid coordinates for Dhaka North (DNCC)
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

# Centroid coordinates for Dhaka South (DSCC)
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
}

# Centroid coordinates for Chattogram (CCC)
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

# Centroid coordinates for Gazipur (GCC)
GCC_COORDS = {
    f"GCC_Ward_{i:02d}": (23.985 + (i * 0.012), 90.380 + ((i % 3) * 0.015), f"Gazipur Sector {i}")
    for i in range(1, 9)
}

# Centroid coordinates for Narayanganj (NCC)
NCC_COORDS = {
    f"NCC_Ward_{i:02d}": (23.615 + (i * 0.010), 90.490 + ((i % 2) * 0.012), f"Narayanganj Zone {i}")
    for i in range(1, 8)
}

# Unified map
ALL_WARD_COORDS = {
    **DNCC_COORDS,
    **DSCC_COORDS,
    **CCC_COORDS,
    **GCC_COORDS,
    **NCC_COORDS
}


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
