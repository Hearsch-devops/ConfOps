#!/bin/bash
# delete_all_bookings_no_jq.sh
# Delete all bookings via API without jq

API_URL="http://192.168.48.159:30500/api/bookings"

echo "Fetching all bookings..."
# Get all bookings and extract IDs using grep/sed
BOOKING_IDS=$(curl -s $API_URL | grep -o '"id":[0-9]*' | sed 's/"id"://')

if [ -z "$BOOKING_IDS" ]; then
    echo "No bookings found."
    exit 0
fi

# Delete each booking
for id in $BOOKING_IDS; do
    echo "Deleting booking ID: $id..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$API_URL/$id")
    if [ "$RESPONSE" -eq 200 ] || [ "$RESPONSE" -eq 204 ]; then
        echo "✅ Booking ID $id deleted."
    else
        echo "❌ Failed to delete booking ID $id (HTTP $RESPONSE)."
    fi
done

echo "All bookings deleted."
