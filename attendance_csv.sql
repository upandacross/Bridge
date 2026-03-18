-- SQL Script to export attendance CSV for a specific date
-- Usage: sqlite3 bridge.db -header -csv ".param set target_date 20260319" < attendance_csv.sql
-- Or: sqlite3 bridge.db -header -csv ".param set :target_date 20260319" < attendance_csv.sql

-- Get target date from parameter (must be set before running this script)
WITH input_date AS (
    SELECT COALESCE(:target_date, '20260205') AS target_date
),
game_info AS (
    SELECT 
        g.id AS game_id,
        g.game_date,
        g.day_type
    FROM Games g
    CROSS JOIN input_date id
    WHERE g.game_date = id.target_date
)
-- Main query
SELECT 
    u.last || ', ' || u.first AS "Name",
    u.phone AS "Phone",
    u.email AS "Email",
    CASE 
        WHEN u.prefer_email = 1 THEN 'email'
        WHEN u.prefer_text = 1 THEN 'text'
        WHEN u.prefer_phone = 1 THEN 'phone'
        ELSE 'none'
    END AS "Preference",
    gi.game_date AS "Date",
    gi.day_type AS "Day Type",
    COALESCE(a.status, 'Absent') AS "Attendance"
FROM Users u
CROSS JOIN game_info gi
LEFT JOIN Attendance a ON u.id = a.user_id AND a.game_id = gi.game_id
WHERE u.active = 1
  AND (
      (u.play_thursdays = 1 AND gi.day_type = 'Thursday')
      OR (u.play_fridays = 1 AND gi.day_type = 'Friday')
  )
ORDER BY "Name";
