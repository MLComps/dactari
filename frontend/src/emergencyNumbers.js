/**
 * Emergency Numbers Database
 * Comprehensive list of emergency numbers by country code (ISO 3166-1 alpha-2)
 * Focus on African countries + common international
 */

export const EMERGENCY_NUMBERS = {
  // East Africa
  KE: { // Kenya
    country: "Kenya",
    ambulance: "999",
    police: "999",
    fire: "999",
    general: "112",
    display: "999",
    specialized: [
      { name: "AMREF Flying Doctors", number: "0800 723 253" },
      { name: "Kenya Red Cross", number: "1199" },
    ]
  },
  RW: { // Rwanda
    country: "Rwanda",
    ambulance: "912",
    police: "113",
    fire: "111",
    general: "112",
    display: "912",
    specialized: [
      { name: "SAMU Ambulance", number: "912" },
    ]
  },
  TZ: { // Tanzania
    country: "Tanzania",
    ambulance: "114",
    police: "112",
    fire: "114",
    general: "112",
    display: "114",
    specialized: []
  },
  UG: { // Uganda
    country: "Uganda",
    ambulance: "911",
    police: "999",
    fire: "999",
    general: "112",
    display: "911",
    specialized: [
      { name: "Uganda Red Cross", number: "0800 100 066" },
    ]
  },
  ET: { // Ethiopia
    country: "Ethiopia",
    ambulance: "907",
    police: "911",
    fire: "939",
    general: "991",
    display: "907",
    specialized: []
  },
  SS: { // South Sudan
    country: "South Sudan",
    ambulance: "999",
    police: "999",
    fire: "998",
    general: "999",
    display: "999",
    specialized: []
  },
  BI: { // Burundi
    country: "Burundi",
    ambulance: "118",
    police: "117",
    fire: "118",
    general: "112",
    display: "118",
    specialized: []
  },
  SO: { // Somalia
    country: "Somalia",
    ambulance: "999",
    police: "888",
    fire: "555",
    general: "999",
    display: "999",
    specialized: []
  },
  DJ: { // Djibouti
    country: "Djibouti",
    ambulance: "351351",
    police: "17",
    fire: "18",
    general: "17",
    display: "17",
    specialized: []
  },
  ER: { // Eritrea
    country: "Eritrea",
    ambulance: "114",
    police: "113",
    fire: "116",
    general: "112",
    display: "114",
    specialized: []
  },

  // Southern Africa
  ZA: { // South Africa
    country: "South Africa",
    ambulance: "10177",
    police: "10111",
    fire: "10177",
    general: "112",
    display: "10177",
    specialized: [
      { name: "Netcare 911", number: "082 911" },
      { name: "ER24", number: "084 124" },
      { name: "Poison Centre", number: "0861 555 777" },
    ]
  },
  ZW: { // Zimbabwe
    country: "Zimbabwe",
    ambulance: "994",
    police: "995",
    fire: "993",
    general: "112",
    display: "994",
    specialized: []
  },
  BW: { // Botswana
    country: "Botswana",
    ambulance: "997",
    police: "999",
    fire: "998",
    general: "112",
    display: "997",
    specialized: []
  },
  NA: { // Namibia
    country: "Namibia",
    ambulance: "211111",
    police: "10111",
    fire: "211111",
    general: "112",
    display: "112",
    specialized: []
  },
  MW: { // Malawi
    country: "Malawi",
    ambulance: "998",
    police: "997",
    fire: "999",
    general: "112",
    display: "998",
    specialized: []
  },
  ZM: { // Zambia
    country: "Zambia",
    ambulance: "991",
    police: "999",
    fire: "993",
    general: "112",
    display: "991",
    specialized: []
  },
  MZ: { // Mozambique
    country: "Mozambique",
    ambulance: "117",
    police: "119",
    fire: "198",
    general: "112",
    display: "117",
    specialized: []
  },
  AO: { // Angola
    country: "Angola",
    ambulance: "116",
    police: "113",
    fire: "115",
    general: "112",
    display: "116",
    specialized: []
  },
  SZ: { // Eswatini (Swaziland)
    country: "Eswatini",
    ambulance: "977",
    police: "999",
    fire: "933",
    general: "112",
    display: "977",
    specialized: []
  },
  LS: { // Lesotho
    country: "Lesotho",
    ambulance: "121",
    police: "123",
    fire: "122",
    general: "112",
    display: "121",
    specialized: []
  },
  MG: { // Madagascar
    country: "Madagascar",
    ambulance: "117",
    police: "117",
    fire: "118",
    general: "117",
    display: "117",
    specialized: []
  },
  MU: { // Mauritius
    country: "Mauritius",
    ambulance: "114",
    police: "112",
    fire: "115",
    general: "112",
    display: "114",
    specialized: []
  },

  // West Africa
  NG: { // Nigeria
    country: "Nigeria",
    ambulance: "112",
    police: "199",
    fire: "112",
    general: "112",
    display: "112",
    specialized: [
      { name: "LASEMA (Lagos)", number: "112" },
      { name: "NEMA", number: "0800 225 6362" },
    ]
  },
  GH: { // Ghana
    country: "Ghana",
    ambulance: "193",
    police: "191",
    fire: "192",
    general: "112",
    display: "193",
    specialized: [
      { name: "National Ambulance", number: "193" },
    ]
  },
  SN: { // Senegal
    country: "Senegal",
    ambulance: "1515",
    police: "17",
    fire: "18",
    general: "112",
    display: "1515",
    specialized: []
  },
  CI: { // Ivory Coast (Cote d'Ivoire)
    country: "Ivory Coast",
    ambulance: "185",
    police: "111",
    fire: "180",
    general: "112",
    display: "185",
    specialized: []
  },
  CM: { // Cameroon
    country: "Cameroon",
    ambulance: "119",
    police: "117",
    fire: "118",
    general: "112",
    display: "119",
    specialized: []
  },
  ML: { // Mali
    country: "Mali",
    ambulance: "15",
    police: "17",
    fire: "18",
    general: "112",
    display: "15",
    specialized: []
  },
  BF: { // Burkina Faso
    country: "Burkina Faso",
    ambulance: "112",
    police: "17",
    fire: "18",
    general: "112",
    display: "112",
    specialized: []
  },
  NE: { // Niger
    country: "Niger",
    ambulance: "15",
    police: "17",
    fire: "18",
    general: "112",
    display: "15",
    specialized: []
  },
  TG: { // Togo
    country: "Togo",
    ambulance: "8200",
    police: "117",
    fire: "118",
    general: "112",
    display: "8200",
    specialized: []
  },
  BJ: { // Benin
    country: "Benin",
    ambulance: "112",
    police: "117",
    fire: "118",
    general: "112",
    display: "112",
    specialized: []
  },
  GN: { // Guinea
    country: "Guinea",
    ambulance: "442020",
    police: "117",
    fire: "118",
    general: "112",
    display: "112",
    specialized: []
  },
  SL: { // Sierra Leone
    country: "Sierra Leone",
    ambulance: "999",
    police: "999",
    fire: "999",
    general: "999",
    display: "999",
    specialized: []
  },
  LR: { // Liberia
    country: "Liberia",
    ambulance: "911",
    police: "911",
    fire: "911",
    general: "911",
    display: "911",
    specialized: []
  },
  GM: { // Gambia
    country: "Gambia",
    ambulance: "116",
    police: "117",
    fire: "118",
    general: "112",
    display: "116",
    specialized: []
  },
  GW: { // Guinea-Bissau
    country: "Guinea-Bissau",
    ambulance: "119",
    police: "117",
    fire: "118",
    general: "112",
    display: "119",
    specialized: []
  },
  CV: { // Cape Verde
    country: "Cape Verde",
    ambulance: "130",
    police: "132",
    fire: "131",
    general: "112",
    display: "130",
    specialized: []
  },
  MR: { // Mauritania
    country: "Mauritania",
    ambulance: "101",
    police: "117",
    fire: "118",
    general: "112",
    display: "101",
    specialized: []
  },

  // North Africa
  EG: { // Egypt
    country: "Egypt",
    ambulance: "123",
    police: "122",
    fire: "180",
    general: "112",
    display: "123",
    specialized: []
  },
  MA: { // Morocco
    country: "Morocco",
    ambulance: "15",
    police: "19",
    fire: "15",
    general: "112",
    display: "15",
    specialized: []
  },
  DZ: { // Algeria
    country: "Algeria",
    ambulance: "14",
    police: "17",
    fire: "14",
    general: "112",
    display: "14",
    specialized: []
  },
  TN: { // Tunisia
    country: "Tunisia",
    ambulance: "190",
    police: "197",
    fire: "198",
    general: "112",
    display: "190",
    specialized: []
  },
  LY: { // Libya
    country: "Libya",
    ambulance: "1515",
    police: "1515",
    fire: "1515",
    general: "112",
    display: "1515",
    specialized: []
  },
  SD: { // Sudan
    country: "Sudan",
    ambulance: "999",
    police: "999",
    fire: "998",
    general: "999",
    display: "999",
    specialized: []
  },

  // Central Africa
  CD: { // DR Congo
    country: "DR Congo",
    ambulance: "112",
    police: "112",
    fire: "118",
    general: "112",
    display: "112",
    specialized: []
  },
  CG: { // Congo (Brazzaville)
    country: "Congo",
    ambulance: "112",
    police: "117",
    fire: "118",
    general: "112",
    display: "112",
    specialized: []
  },
  CF: { // Central African Republic
    country: "Central African Republic",
    ambulance: "1220",
    police: "117",
    fire: "118",
    general: "112",
    display: "1220",
    specialized: []
  },
  TD: { // Chad
    country: "Chad",
    ambulance: "112",
    police: "17",
    fire: "18",
    general: "112",
    display: "112",
    specialized: []
  },
  GA: { // Gabon
    country: "Gabon",
    ambulance: "1300",
    police: "1730",
    fire: "18",
    general: "112",
    display: "1300",
    specialized: []
  },
  GQ: { // Equatorial Guinea
    country: "Equatorial Guinea",
    ambulance: "112",
    police: "114",
    fire: "115",
    general: "112",
    display: "112",
    specialized: []
  },
  ST: { // Sao Tome and Principe
    country: "Sao Tome and Principe",
    ambulance: "112",
    police: "112",
    fire: "112",
    general: "112",
    display: "112",
    specialized: []
  },

  // International / Common
  US: { // United States
    country: "United States",
    ambulance: "911",
    police: "911",
    fire: "911",
    general: "911",
    display: "911",
    specialized: [
      { name: "Poison Control", number: "1-800-222-1222" },
      { name: "Suicide Prevention", number: "988" },
    ]
  },
  GB: { // United Kingdom
    country: "United Kingdom",
    ambulance: "999",
    police: "999",
    fire: "999",
    general: "112",
    display: "999",
    specialized: [
      { name: "NHS Non-Emergency", number: "111" },
    ]
  },
  FR: { // France
    country: "France",
    ambulance: "15",
    police: "17",
    fire: "18",
    general: "112",
    display: "15",
    specialized: []
  },
  DE: { // Germany
    country: "Germany",
    ambulance: "112",
    police: "110",
    fire: "112",
    general: "112",
    display: "112",
    specialized: []
  },
  IN: { // India
    country: "India",
    ambulance: "102",
    police: "100",
    fire: "101",
    general: "112",
    display: "112",
    specialized: []
  },
  CN: { // China
    country: "China",
    ambulance: "120",
    police: "110",
    fire: "119",
    general: "112",
    display: "120",
    specialized: []
  },
  AE: { // UAE
    country: "UAE",
    ambulance: "998",
    police: "999",
    fire: "997",
    general: "112",
    display: "998",
    specialized: []
  },
  SA: { // Saudi Arabia
    country: "Saudi Arabia",
    ambulance: "997",
    police: "999",
    fire: "998",
    general: "112",
    display: "997",
    specialized: []
  },
}

// Default fallback for unknown locations
export const DEFAULT_EMERGENCY = {
  country: "International",
  ambulance: "112",
  police: "112",
  fire: "112",
  general: "112",
  display: "112",
  specialized: [],
  note: "112 is the international emergency number recognized in most countries"
}

/**
 * Get emergency numbers for a country code
 */
export function getEmergencyNumbers(countryCode) {
  if (!countryCode) return DEFAULT_EMERGENCY
  const upper = countryCode.toUpperCase()
  return EMERGENCY_NUMBERS[upper] || DEFAULT_EMERGENCY
}

/**
 * Reverse geocode coordinates to get country code
 * Uses free BigDataCloud API (no key required for basic usage)
 */
export async function getCountryFromCoords(latitude, longitude) {
  try {
    const response = await fetch(
      `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${latitude}&longitude=${longitude}&localityLanguage=en`
    )

    if (!response.ok) {
      throw new Error('Geocoding failed')
    }

    const data = await response.json()
    return {
      countryCode: data.countryCode,
      countryName: data.countryName,
      city: data.city || data.locality || data.principalSubdivision,
      success: true
    }
  } catch (error) {
    console.error('Reverse geocoding error:', error)
    return {
      countryCode: null,
      countryName: null,
      city: null,
      success: false,
      error: error.message
    }
  }
}

/**
 * Get user's current location
 * Returns a promise with coordinates
 */
export function getCurrentPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation not supported'))
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          success: true
        })
      },
      (error) => {
        let message = 'Location access denied'
        switch (error.code) {
          case error.PERMISSION_DENIED:
            message = 'Location permission denied'
            break
          case error.POSITION_UNAVAILABLE:
            message = 'Location unavailable'
            break
          case error.TIMEOUT:
            message = 'Location request timed out'
            break
        }
        reject(new Error(message))
      },
      {
        enableHighAccuracy: false,
        timeout: 10000,
        maximumAge: 300000 // Cache for 5 minutes
      }
    )
  })
}

/**
 * Full flow: Get location -> Get country -> Get emergency numbers
 */
export async function detectEmergencyNumbers() {
  try {
    // Get coordinates
    const position = await getCurrentPosition()

    // Get country from coordinates
    const location = await getCountryFromCoords(position.latitude, position.longitude)

    if (!location.success || !location.countryCode) {
      return {
        success: false,
        emergency: DEFAULT_EMERGENCY,
        location: null,
        error: 'Could not determine country'
      }
    }

    // Get emergency numbers for country
    const emergency = getEmergencyNumbers(location.countryCode)

    return {
      success: true,
      emergency,
      location: {
        country: location.countryName,
        countryCode: location.countryCode,
        city: location.city,
        coords: {
          lat: position.latitude,
          lng: position.longitude
        }
      }
    }
  } catch (error) {
    return {
      success: false,
      emergency: DEFAULT_EMERGENCY,
      location: null,
      error: error.message
    }
  }
}
