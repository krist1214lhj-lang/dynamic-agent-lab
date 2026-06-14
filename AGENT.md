# dynamic-agent-lab

## Project Purpose

`dynamic-agent-lab` is a FastAPI web app that receives a travel request, automatically selects the needed independent agents, runs them, and combines their results.

Users can enter travel conditions through the UI selection panel or through an additional free-text request. The app loads `travel_*` agents from the external agent library and integrates their outputs.

The long-term goal is to evolve this project into a stable, deployable travel agent app.

## App Location

```bash
/mnt/d/CodexWork/test-01/dynamic-agent-lab
```

## External Agent Library

Primary agent library:

```bash
/mnt/d/CodexWork/test-01/dynamic-agent-lab/agents
```

Development fallback:

```bash
/mnt/d/AI_AGENT_LIBRARY
```

## External Agents

- `travel_destination_agent`
- `travel_budget_agent`
- `travel_schedule_agent`
- `travel_weather_agent`
- `travel_tour_agent`
- `travel_transport_agent`
- `travel_food_agent`
- `travel_event_agent`

## Agent Roles

- `travel_destination_agent`: travel destination recommendations and destination summaries
- `travel_budget_agent`: budget, costs, and saving tips
- `travel_schedule_agent`: travel itinerary
- `travel_weather_agent`: weather from KMA API or `mock_fallback`
- `travel_tour_agent`: tour attractions from Korea Tourism Organization TourAPI or `mock_fallback`
- `travel_transport_agent`: transport and route planning
- `travel_food_agent`: restaurants and local food recommendations from TourAPI or `mock_fallback`
- `travel_event_agent`: regional festivals and cultural events from TourAPI or `mock_fallback`

## External Agent Rules

- Each agent folder must contain `agent.json`, `main.py`, and `README.md`.
- Each agent `main.py` must expose `run(input_data)`.
- `run(input_data)` must return a JSON-compatible `dict`.
- If an external API fails, the app must not crash and the agent should return `mock_fallback`.
- Full API keys must never be printed or written to logs.
- Agents must prioritize `input_data.destination`, `input_data.location`, `input_data.origin`, `input_data.days`, and `input_data.budget_level`.
- API keys and `.env` files must not be stored in the repository.

## `main.py` Responsibilities

- Define the FastAPI app.
- Serve `static/index.html` from `GET /`.
- Handle `POST /run-workflow`.
- Merge the user request and UI selections into `input_data`.
- Select `selected_agents` using `requested_features` or keyword routing.
- Read each external agent's `agent.json`.
- Fresh-load each external agent's `main.py` and run `run(input_data)`.
- Return `selected_agents`, `loaded_agents`, `agent_results`, `final_summary`, and `input_data_summary`.

## `static/index.html` Responsibilities

- Display the UI selection panel.
- Provide controls for destination, origin, duration, budget, requested information checkboxes, and additional request text.
- Call `/run-workflow`.
- Display `selected_agents`, `loaded_agents`, `agent_results`, and `final_summary`.
- Render dedicated HTML cards for agents such as weather, tour, and transport.
- Keep `raw_response` and `debug_info` available in `details` areas.

## Planned UI Improvements

- UI selection panel
- Agent execution flow display
- `input_data` and `debug_info` panel
- Agent library gallery

## Modification Principles

- Modify one feature at a time.
- Clearly identify the target file before editing.
- Prefer separating `main.py` changes from `static/index.html` changes.
- When modifying an external agent, edit only that agent's folder.
- Preserve existing behavior unless the task explicitly changes it.
- Public API failures must not crash the app.
- After testing, summarize changed files and test results.

## New Feature Checklist

When adding a new requested feature, always check these five places together:

1. Create or update `agents/<new_agent>`.
2. Add the feature key to `main.py` `FEATURE_AGENT_MAP`.
3. Add the matching checkbox `value` to `static/index.html`.
4. Add or update the result card renderer in `static/index.html`.
5. Add a standalone feature test to `scripts/smoke_test.py`.

Do not add only a UI checkbox while omitting `main.py` `FEATURE_AGENT_MAP`.
Do not treat a request as successful if `requested_features` is present but `selected_agents` is empty and falls back to `travel_destination_agent`.
Every new feature must pass a standalone smoke test before the feature is considered complete.

## Server Command

```bash
cd /mnt/d/CodexWork/test-01/dynamic-agent-lab
uvicorn main:app --host 0.0.0.0 --port 8013 --reload --reload-dir /mnt/d/CodexWork/test-01/dynamic-agent-lab --reload-dir /mnt/d/AI_AGENT_LIBRARY
```

## Test Conditions

- Destination: 부산
- Origin: 서울
- Duration: 2박 3일
- Budget: 저렴
- Requested information: 여행지 추천, 예산, 일정, 날씨, 관광지, 교통
- Additional request may be blank and the workflow must still run.

## Completion Verification

- Any change is complete only after `scripts/verify_local_and_vercel.py` passes.
- The script must compare the local app and the Vercel deployment before the task is considered done.
- The default local URL is `http://127.0.0.1:8013`.
- Use the default deployment URL or override it with `VERCEL_URL` / `--vercel-url` when needed.
- Override the local URL with `LOCAL_URL` / `--local-url` when a different port is required.

PowerShell:

```powershell
python scripts\verify_local_and_vercel.py
```

WSL/Linux:

```bash
python3 scripts/verify_local_and_vercel.py
```

## Success Criteria

- `selected_agents` includes `travel_destination_agent`, `travel_budget_agent`, `travel_schedule_agent`, `travel_weather_agent`, `travel_tour_agent`, and `travel_transport_agent`.
- `input_data_summary.destination` is `부산`.
- `input_data_summary.days` is `3`.
- `travel_weather_agent` returns weather based on `location`.
- `travel_tour_agent` returns attractions based on `destination`.
- `travel_transport_agent` returns route information from `origin` to `destination`.
