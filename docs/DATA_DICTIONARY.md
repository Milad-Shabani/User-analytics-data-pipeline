# Data Dictionary

## Source: `user_profiles.csv`

| field              | type | notes                                   |
|--------------------|------|------------------------------------------|
| user_id            | int  | primary key                              |
| name               | str  |                                            |
| registration_date  | date | ISO-8601 (`YYYY-MM-DD`)                  |
| location           | str  | free-text city name                       |

## Source: `user_events_YYYYMMDD.json`

| field       | type   | notes                                              |
|-------------|--------|------------------------------------------------------|
| user_id     | int    | joins to `user_profiles.user_id`                     |
| event_type  | str    | `page_view`, `button_click`, `purchase`, `app_open`, `app_close`, or new values as the product evolves |
| timestamp   | str    | ISO-8601 with `Z` suffix (UTC)                       |
| details     | object | shape depends on `event_type`; may be `{}`           |

Known `details` fields, by `event_type` (not exhaustive — anything else
lands in `details_raw` untouched):

| event_type    | typical `details` fields                          |
|---------------|------------------------------------------------------|
| page_view     | `page_url`, `referrer`, `duration_ms`, `item_count`  |
| button_click  | `button_id`, `filter_param`                          |
| purchase      | `item_id`, `price`, `quantity`, `currency`           |
| app_close     | `duration_session_ms`                                |
| app_open      | *(usually empty)*                                    |

## Output: `dim_user_profiles`

Same shape as the source CSV, de-duplicated on `user_id` (latest row wins).

## Output: `fact_user_activity`

| column               | type      | notes                                              |
|----------------------|-----------|------------------------------------------------------|
| event_id             | str       | deterministic hash, primary key                     |
| user_id              | int       |                                                        |
| name                 | str       | from `dim_user_profiles`; null for orphan events     |
| location             | str       | from `dim_user_profiles`                             |
| registration_date    | date      | from `dim_user_profiles`                             |
| event_type           | str       |                                                        |
| timestamp            | datetime  | UTC                                                    |
| event_date           | date      | `timestamp` truncated to day; Parquet partition key  |
| details_raw          | str(json) | original `details` payload, verbatim                 |
| page_url             | str       | flattened from `details`, nullable                    |
| referrer             | str       | flattened from `details`, nullable                    |
| duration_ms          | int       | flattened from `details`, nullable                    |
| button_id            | str       | flattened from `details`, nullable                    |
| filter_param         | str       | flattened from `details`, nullable                    |
| item_id              | str       | flattened from `details`, nullable                    |
| price                | number    | flattened from `details`, nullable                    |
| quantity             | int       | flattened from `details`, nullable                    |
| currency             | str       | flattened from `details`, nullable                    |
| item_count           | int       | flattened from `details`, nullable                    |
| duration_session_ms  | int       | flattened from `details`, nullable                    |
