#!/bin/bash
# modify_random_bookings.sh
# Randomly modify 5 existing bookings

API_BASE="http://192.168.48.159:30500/api"
BOOKINGS_API="$API_BASE/bookings"

MODIFY_COUNT=5
MAX_RETRIES=5

echo "📥 Fetching existing bookings..."

# NOTE: This assumes GET /api/bookings exists
BOOKING_IDS=($(curl -s "$BOOKINGS_API" | grep -o '"id":[0-9]*' | sed 's/"id"://'))

if [ ${#BOOKING_IDS[@]} -eq 0 ]; then
    echo "❌ No bookings found to modify."
    exit 0
fi

# Shuffle and pick N bookings
SHUFFLED_IDS=($(printf "%s\n" "${BOOKING_IDS[@]}" | shuf))
TARGET_IDS=("${SHUFFLED_IDS[@]:0:$MODIFY_COUNT}")

echo "🔄 Selected bookings to modify: ${TARGET_IDS[*]}"
echo

for BOOKING_ID in "${TARGET_IDS[@]}"; do
    RETRY=0

    while [ $RETRY -lt $MAX_RETRIES ]; do
        # Random future date (next 7 days)
        DATE=$(date -d "+$((RANDOM % 7 + 1)) days" +"%Y-%m-%d")

        # Working hours 9–18
        HOUR=$((9 + RANDOM % 9))
        MINUTE=$((RANDOM % 2 * 30))
        TIME=$(printf "%02d:%02d" $HOUR $MINUTE)

        # Duration
        DURATIONS=(30 60 90)
        DURATION=${DURATIONS[$((RANDOM % 3))]}

        RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
            -X PUT "$BOOKINGS_API/$BOOKING_ID" \
            -H "Content-Type: application/json" \
            -d "{
                \"date\": \"$DATE\",
                \"time\": \"$TIME\",
                \"duration\": $DURATION
            }")

        if [ "$RESPONSE" -eq 200 ]; then
            echo "✅ Booking $BOOKING_ID modified → $DATE $TIME ($DURATION min)"
            break
        elif [ "$RESPONSE" -eq 409 ]; then
            echo "⚠️ Conflict for booking $BOOKING_ID, retrying..."
            ((RETRY++))
        elif [ "$RESPONSE" -eq 400 ]; then
            echo "⚠️ Booking $BOOKING_ID already modified or invalid update"
            break
        else
            echo "❌ Failed to modify booking $BOOKING_ID (HTTP $RESPONSE)"
            break
        fi
    done
done

echo
echo "✅ Random booking modification process completed."
