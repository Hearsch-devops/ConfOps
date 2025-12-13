#!/bin/bash
# realistic_random_bookings_retry.sh
# Create 20 realistic bookings with conflict handling

API_URL="http://192.168.48.159:30500/api/bookings"

ROOMS=("1" "2" "3")
ROOM_NAMES=("Executive Board Room" "Innovation Hub" "Focus Room")
ROOM_CAPACITY=(12 8 4)

NAMES=("Alice" "Bob" "Charlie" "David" "Eve" "Frank" "Grace" "Hannah" "Ivan" "Judy" "Kyle" "Laura" "Mike" "Nina" "Oscar" "Paula" "Quinn" "Rachel" "Steve" "Tina")
EMAILS=("alice@example.com" "bob@example.com" "charlie@example.com" "david@example.com" "eve@example.com" "frank@example.com" "grace@example.com" "hannah@example.com" "ivan@example.com" "judy@example.com" "kyle@example.com" "laura@example.com" "mike@example.com" "nina@example.com" "oscar@example.com" "paula@example.com" "quinn@example.com" "rachel@example.com" "steve@example.com" "tina@example.com")
DURATIONS=(30 60 90)

declare -A ROOM_SCHEDULE  # track used times per room/day in script run
TOTAL_BOOKINGS=20
MAX_RETRIES=10

for ((i=0;i<TOTAL_BOOKINGS;i++)); do
    RETRY=0
    while [ $RETRY -lt $MAX_RETRIES ]; do
        ROOM_INDEX=$((RANDOM % 3))
        ROOM_ID=${ROOMS[$ROOM_INDEX]}
        ROOM_NAME=${ROOM_NAMES[$ROOM_INDEX]}
        MAX_ATTENDEES=${ROOM_CAPACITY[$ROOM_INDEX]}

        ATTENDEES=$((1 + RANDOM % MAX_ATTENDEES))
        DAY_OFFSET=$((RANDOM % 7))
        DATE=$(date -d "+$DAY_OFFSET days" +"%Y-%m-%d")

        HOUR=$((9 + RANDOM % 9))
        MINUTE=$((RANDOM % 2 * 30))
        TIME=$(printf "%02d:%02d" $HOUR $MINUTE)

        DURATION=${DURATIONS[$((RANDOM % 3))]}

        # Check for overlap in this script run
        KEY="$ROOM_ID-$DATE-$TIME"
        if [[ -n "${ROOM_SCHEDULE[$KEY]}" ]]; then
            ((RETRY++))
            continue
        fi

        NAME=${NAMES[$i]}
        EMAIL=${EMAILS[$i]}
        PURPOSE="Project meeting with $NAME"

        RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $API_URL \
            -H "Content-Type: application/json" \
            -d "{
                \"room_id\": $ROOM_ID,
                \"name\": \"$NAME\",
                \"email\": \"$EMAIL\",
                \"date\": \"$DATE\",
                \"time\": \"$TIME\",
                \"duration\": $DURATION,
                \"attendees\": $ATTENDEES,
                \"purpose\": \"$PURPOSE\"
            }")

        if [ "$RESPONSE" -eq 200 ] || [ "$RESPONSE" -eq 201 ]; then
            echo "✅ Booking $i: $NAME in $ROOM_NAME on $DATE at $TIME for $DURATION min, $ATTENDEES attendees"
            ROOM_SCHEDULE[$KEY]=1
            break
        elif [ "$RESPONSE" -eq 409 ]; then
            echo "⚠️ Booking conflict for $NAME in $ROOM_NAME on $DATE at $TIME, retrying..."
            ((RETRY++))
            continue
        else
            echo "❌ Booking $i FAILED for $NAME in $ROOM_NAME on $DATE at $TIME (HTTP $RESPONSE)"
            break
        fi
    done

    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "❌ Booking $i: Could not find a free slot for $NAME after $MAX_RETRIES retries."
    fi
done
