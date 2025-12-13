#!/bin/bash
# cancel_random_bookings.sh
# Randomly cancel existing bookings

API_BASE="http://192.168.48.159:30500/api"
BOOKINGS_API="$API_BASE/bookings"

CANCEL_COUNT=5

echo "📥 Fetching existing bookings..."

# Fetch booking IDs (requires GET /api/bookings)
BOOKING_IDS=($(curl -s "$BOOKINGS_API" | grep -o '"id":[0-9]*' | sed 's/"id"://'))

TOTAL=${#BOOKING_IDS[@]}

if [ "$TOTAL" -eq 0 ]; then
    echo "❌ No bookings found to cancel."
    exit 0
fi

# Adjust cancel count if fewer bookings exist
if [ "$TOTAL" -lt "$CANCEL_COUNT" ]; then
    CANCEL_COUNT=$TOTAL
fi

# Shuffle and pick N booking IDs
TARGET_IDS=($(printf "%s\n" "${BOOKING_IDS[@]}" | shuf | head -n "$CANCEL_COUNT"))

echo "🗑️ Selected bookings to cancel: ${TARGET_IDS[*]}"
echo

for BOOKING_ID in "${TARGET_IDS[@]}"; do
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X DELETE "$BOOKINGS_API/$BOOKING_ID")

    if [ "$RESPONSE" -eq 200 ] || [ "$RESPONSE" -eq 204 ]; then
        echo "✅ Booking $BOOKING_ID cancelled successfully"
    elif [ "$RESPONSE" -eq 404 ]; then
        echo "⚠️ Booking $BOOKING_ID not found (already deleted?)"
    else
        echo "❌ Failed to cancel booking $BOOKING_ID (HTTP $RESPONSE)"
    fi
done

echo
echo "✅ Random booking cancellation completed."
