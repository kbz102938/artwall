import { NextRequest, NextResponse } from "next/server";
// import { PubSub } from "@google-cloud/pubsub";

interface ActivityEvent {
  visitorId: string;
  sessionId: string;
  event: string;
  paintingId?: string;
  position?: number;
  source?: string;
  metadata?: Record<string, unknown>;
  timestamp?: number;
}

// Initialize Pub/Sub client (uncomment when GCP is set up)
// const pubsub = new PubSub();
// const topicName = "artwall-activities";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { events } = body as { events: ActivityEvent[] };

    if (!events || !Array.isArray(events) || events.length === 0) {
      return NextResponse.json(
        { error: "No events provided" },
        { status: 400 }
      );
    }

    // Validate events
    const validEvents = events.filter(
      (e) => e.visitorId && e.event
    );

    if (validEvents.length === 0) {
      return NextResponse.json(
        { error: "No valid events" },
        { status: 400 }
      );
    }

    // Add server timestamp
    const enrichedEvents = validEvents.map((e) => ({
      ...e,
      serverTimestamp: Date.now(),
    }));

    // TODO: Publish to Pub/Sub when GCP is set up
    // const messageBuffer = Buffer.from(JSON.stringify(enrichedEvents));
    // await pubsub.topic(topicName).publishMessage({ data: messageBuffer });

    // For now, just log the events
    console.log("Activity events received:", enrichedEvents.length);

    return NextResponse.json({
      success: true,
      logged: enrichedEvents.length,
    });
  } catch (error) {
    console.error("Error processing activity:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
