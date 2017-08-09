import bottle
import requests
import datetime
import argparse
import os

DEFAULT_URL = "https://api.meetup.com/{}/events"

app = bottle.Bottle()
app.config["meetup_api_url"] = DEFAULT_URL

if os.environ.get("MEETUP_API_KEY"):
    app.config["meetup_api_key"] = os.environ.get("MEETUP_API_KEY")


def get_meetup_events(meetups, api_key, url="https://api.meetup.com/{}/events"):
    params = {
        "sign": "true",
        "photo-host": "public",
        "status": "past,upcoming",
        "page": 200,
        "key": api_key
    }
    events = []
    for m in meetups:
        r = requests.get(url.format(m), params=params)
        if r.status_code == requests.codes.ok:
            events += r.json()
        else:
            print("Could not find data for {}".format(m))
    return events


def process_meetup_events(events):
    for e in events:
        for d in ["time", "created", "updated"]:
            if not isinstance(e[d], datetime.datetime):
                e[d] = datetime.datetime.fromtimestamp(e[d] / 1000)
        if e.get("group", {}).get("created") and not isinstance(e["group"]["created"], datetime.datetime):
            e["group"]["created"] = datetime.datetime.fromtimestamp(e["group"]["created"] / 1000)
        if e.get("duration") and not isinstance(e["duration"], datetime.timedelta):
            e["duration"] = datetime.timedelta(milliseconds=e["duration"])
    return events


def events_to_timeline(events):
    timeline = {
        "events": []
    }
    for e in events:
        timeline["events"].append({
            "start_date": {
                "year": e["time"].year,
                "month": e["time"].month,
                "day": e["time"].day,
                "hour": e["time"].hour,
                "minute": e["time"].minute,
            },
            "text": {
                "headline": e.get("name", ""),
                "text": e.get("description", ""),
            },
            "group": e.get("group", {}).get("name", ""),
            "unique_id": e["id"],
        })
    return timeline


@app.route('/api/<meetup>')
def api(meetup):
    meetup = meetup.split("+")
    events = get_meetup_events(meetup, app.config["meetup_api_key"], url=app.config["meetup_api_url"])
    events = process_meetup_events(events)
    return events_to_timeline(events)


@app.route('/timeline/<meetup>')
@bottle.view('timeline.html')
def timeline(meetup):
    return dict(meetup=meetup)


def main():
    parser = argparse.ArgumentParser(description='Server for turning meetup.com API data into a timeline.')

    # server options
    parser.add_argument('-host', '--host', default="localhost", help='host for the server')
    parser.add_argument('-p', '--port', default=8080, help='port for the server')
    parser.add_argument('--debug', action='store_true', dest="debug", help='Debug mode (autoreloads the server)')
    parser.add_argument('--server', default="auto", help='Server backend to use (see http://bottlepy.org/docs/dev/deployment.html#switching-the-server-backend)')

    # meetup options
    parser.add_argument('--meetup-api-key', help="Meetup API key (see https://secure.meetup.com/meetup_api/key/)")
    parser.add_argument('--meetup-api-url', default=DEFAULT_URL, help="Meetup API URL for get events endpoint. Use a {} for where the meetup slug should go.")

    args = parser.parse_args()

    app.config["meetup_api_key"] = args.meetup_api_key
    app.config["meetup_api_url"] = args.meetup_api_url

    bottle.debug(args.debug)

    bottle.run(app, server=args.server, host=args.host, port=args.port, reloader=args.debug)

if __name__ == '__main__':
    main()
