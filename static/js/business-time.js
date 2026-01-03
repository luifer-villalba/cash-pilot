/**
 * Business Timezone Utilities
 * 
 * Fetches and caches current date/time for each business based on their configured timezone.
 * Used to ensure dates/times are displayed in the business's local timezone, not the browser's.
 */

// Cache for business time data (1 minute TTL)
const businessTimeCache = new Map();
const CACHE_TTL_MS = 60000; // 1 minute

/**
 * Fetch current time for a business from the API
 * @param {string} businessId - UUID of the business
 * @returns {Promise<Object>} Time data: {date, datetime, time, timezone, utc_offset}
 */
async function fetchBusinessTime(businessId) {
    if (!businessId) {
        throw new Error('businessId is required');
    }

    // Check cache first
    const cached = businessTimeCache.get(businessId);
    if (cached && (Date.now() - cached.timestamp < CACHE_TTL_MS)) {
        return cached.data;
    }

    try {
        const response = await fetch(`/api/current-time?business_id=${businessId}`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch business time');
        }

        const data = await response.json();
        
        // Cache the response
        businessTimeCache.set(businessId, {
            data,
            timestamp: Date.now()
        });

        return data;
    } catch (error) {
        console.error('Error fetching business time:', error);
        // Fallback to browser time if API fails
        const now = new Date();
        return {
            date: now.toISOString().split('T')[0],
            datetime: now.toISOString(),
            time: now.toTimeString().split(' ')[0],
            timezone: 'browser',
            utc_offset: getLocalUTCOffset()
        };
    }
}

/**
 * Get today's date for a business (YYYY-MM-DD format)
 * @param {string} businessId - UUID of the business
 * @returns {Promise<string>} Date in YYYY-MM-DD format
 */
async function getTodayForBusiness(businessId) {
    const timeData = await fetchBusinessTime(businessId);
    return timeData.date;
}

/**
 * Get current time for a business (HH:MM format)
 * @param {string} businessId - UUID of the business
 * @returns {Promise<string>} Time in HH:MM format
 */
async function getCurrentTimeForBusiness(businessId) {
    const timeData = await fetchBusinessTime(businessId);
    // Return time in HH:MM format (without seconds)
    return timeData.time.substring(0, 5);
}

/**
 * Get current datetime for a business
 * @param {string} businessId - UUID of the business
 * @returns {Promise<string>} ISO datetime string
 */
async function getCurrentDateTimeForBusiness(businessId) {
    const timeData = await fetchBusinessTime(businessId);
    return timeData.datetime;
}

/**
 * Get browser's local UTC offset in format "+03:00" or "-03:00"
 * @returns {string} UTC offset
 */
function getLocalUTCOffset() {
    const offset = -new Date().getTimezoneOffset();
    const hours = Math.floor(Math.abs(offset) / 60);
    const minutes = Math.abs(offset) % 60;
    const sign = offset >= 0 ? '+' : '-';
    return `${sign}${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
}

/**
 * Clear cache for a specific business or all businesses
 * @param {string|null} businessId - Business ID to clear, or null to clear all
 */
function clearBusinessTimeCache(businessId = null) {
    if (businessId) {
        businessTimeCache.delete(businessId);
    } else {
        businessTimeCache.clear();
    }
}

/**
 * Prefetch time data for a business (useful for performance)
 * @param {string} businessId - UUID of the business
 */
function prefetchBusinessTime(businessId) {
    fetchBusinessTime(businessId).catch(err => {
        console.warn('Failed to prefetch business time:', err);
    });
}

// Export functions for use in other scripts
window.BusinessTime = {
    fetchBusinessTime,
    getTodayForBusiness,
    getCurrentTimeForBusiness,
    getCurrentDateTimeForBusiness,
    clearBusinessTimeCache,
    prefetchBusinessTime
};
