import sys
import argparse
import logging
import uvicorn
import uuid
from app.config.settings import settings
from app.database.repository import repo
from app.workflow.generate import generate_pipeline
from app.workflow.publish import publish_pipeline

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.LOGS_DIR / "app.log", encoding="utf-8")
    ]
)

logger = logging.getLogger("app.main")

def main():
    parser = argparse.ArgumentParser(description="Kids Animated Video Studio CLI & Server")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: generate
    gen_parser = subparsers.add_parser("generate", help="Generate a new animated video episode")
    gen_parser.add_argument("--topic", type=str, required=True, help="Story topic or theme")
    gen_parser.add_argument("--episode-id", type=str, default=None, help="Custom episode ID")

    # Command: server
    server_parser = subparsers.add_parser("server", help="Start local FastAPI Web Dashboard & Approval server")
    server_parser.add_argument("--port", type=int, default=settings.PORT, help="Port to run server on")
    server_parser.add_argument("--host", type=str, default=settings.HOST, help="Host address")

    # Command: publish
    pub_parser = subparsers.add_parser("publish", help="Publish an approved episode to YouTube")
    pub_parser.add_argument("--episode-id", type=str, required=True, help="Episode ID to publish")
    pub_parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry uploading an episode whose previous publish attempt failed",
    )

    # Command: list
    subparsers.add_parser("list", help="List all generated video episodes")

    args = parser.parse_args()

    if args.command == "generate":
        episode_id = args.episode_id or f"ep_{uuid.uuid4().hex[:8]}"
        logger.info(f"Generating episode for topic: '{args.topic}'...")
        res = generate_pipeline.run_generation_workflow(topic=args.topic, episode_id=episode_id)
        print(f"\nResult: {res}\n")

    elif args.command == "server":
        print(f"\n🚀 Starting Kids Animated Video Dashboard at: http://localhost:{args.port}\n")
        uvicorn.run("app.web.server:app", host=args.host, port=args.port, reload=False)

    elif args.command == "publish":
        logger.info(f"Publishing episode {args.episode_id}...")
        success = publish_pipeline.publish_video(
            args.episode_id,
            retry_failed=args.retry_failed,
        )
        print(f"\nPublished: {success}\n")

    elif args.command == "list":
        videos = repo.list_all()
        print("\n=== Video Episodes Database ===")
        for v in videos:
            print(f"[{v.status.value}] ID: {v.episode_id} | Title: {v.title} | Topic: {v.topic}")
        print()

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
