-- SQL Script to export attendance CSV
-- Usage: sqlite3 bridge_attendance.db -header -csv < export_attendance_csv.sql
-- Or with date parameter: sqlite3 bridge_attendance.db -header -csv ".param set :target_date 'DD/MM/YYYY'" < export_attendance_csv.sql

-- Set the target date (format: DD/MM/YYYY)
-- Modify this value or use .param to set it dynamically
.param init
.param set :target_date '01/01/2024'

-- Get the day, month, year from the target date
WITH target_date AS (
    SELECT 
        CAST(substr(:target_date, 1, 2) AS INTEGER) AS target_day,
        CAST(substr(:target_date, 4, 2) AS INTEGER) AS target_month,
        CAST(substr(:target_date, 7, 4) AS INTEGER) AS target_year
),
-- Get the month record for the target date
month_record AS (
    SELECT 
        id,
        MM,
        YYYY,
        thursdays,
        fridays,
        target_date.target_day,
        target_date.target_month,
        target_date.target_year
    FROM Month_Year_Thursday_Friday
    CROSS JOIN target_date
    WHERE MM = target_date.target_month 
      AND YYYY = target_date.target_year
),
-- Parse dates to find the position of the target date
parsed_dates AS (
    SELECT 
        mr.id,
        mr.MM,
        mr.YYYY,
        mr.target_day,
        mr.target_month,
        mr.target_year,
        -- Split thursdays and find position
        mr.thursdays,
        mr.fridays,
        -- Check if target date is a Thursday
        CASE 
            WHEN instr(mr.thursdays, printf('%04d%02d%02d', mr.YYYY, mr.MM, mr.target_day)) > 0 
            THEN 'Thursday'
            WHEN instr(mr.fridays, printf('%04d%02d%02d', mr.YYYY, mr.MM, mr.target_day)) > 0 
            THEN 'Friday'
            ELSE NULL
        END AS day_type,
        -- Find position in thursdays list
        (
            SELECT COUNT(*) 
            FROM (
                WITH RECURSIVE split(value, rest) AS (
                    SELECT 
                        CASE 
                            WHEN substr(mr.thursdays, 1, instr(mr.thursdays || ',', ',') - 1) = printf('%04d%02d%02d', mr.YYYY, mr.MM, mr.target_day)
                            THEN 1
                            ELSE 0
                        END,
                        substr(mr.thursdays, instr(mr.thursdays || ',', ',') + 1)
                    UNION ALL
                    SELECT 
                        CASE 
                            WHEN substr(rest, 1, instr(rest || ',', ',') - 1) = printf('%04d%02d%02d', mr.YYYY, mr.MM, mr.target_day)
                            THEN 1
                            ELSE 0
                        END,
                        CASE 
                            WHEN instr(rest, ',') > 0 THEN substr(rest, instr(rest, ',') + 1)
                            ELSE ''
                        END
                    FROM split
                    WHERE rest <> ''
                )
                SELECT * FROM split WHERE value = 1
            )
        ) AS thursday_position,
        -- Find position in fridays list
        (
            SELECT COUNT(*) 
            FROM (
                WITH RECURSIVE split(value, rest) AS (
                    SELECT 
                        CASE 
                            WHEN substr(mr.fridays, 1, instr(mr.fridays || ',', ',') - 1) = printf('%04d%02d%02d', mr.YYYY, mr.MM, mr.target_day)
                            THEN 1
                            ELSE 0
                        END,
                        substr(mr.fridays, instr(mr.fridays || ',', ',') + 1)
                    UNION ALL
                    SELECT 
                        CASE 
                            WHEN substr(rest, 1, instr(rest || ',', ',') - 1) = printf('%04d%02d%02d', mr.YYYY, mr.MM, mr.target_day)
                            THEN 1
                            ELSE 0
                        END,
                        CASE 
                            WHEN instr(rest, ',') > 0 THEN substr(rest, instr(rest, ',') + 1)
                            ELSE ''
                        END
                    FROM split
                    WHERE rest <> ''
                )
                SELECT * FROM split WHERE value = 1
            )
        ) AS friday_position
    FROM month_record mr
),
-- Calculate the index position (0-based) for attendance lookup
date_position AS (
    SELECT 
        pd.*,
        CASE 
            WHEN pd.day_type = 'Thursday' THEN 
                (SELECT COUNT(*) - 1 FROM (
                    WITH RECURSIVE split(idx, value, rest) AS (
                        SELECT 0, 
                               substr(pd.thursdays, 1, instr(pd.thursdays || ',', ',') - 1),
                               substr(pd.thursdays, instr(pd.thursdays || ',', ',') + 1)
                        UNION ALL
                        SELECT idx + 1,
                               substr(rest, 1, instr(rest || ',', ',') - 1),
                               CASE WHEN instr(rest, ',') > 0 THEN substr(rest, instr(rest, ',') + 1) ELSE '' END
                        FROM split WHERE rest <> ''
                    )
                    SELECT idx FROM split WHERE value <= printf('%04d%02d%02d', pd.YYYY, pd.MM, pd.target_day)
                      AND value = printf('%04d%02d%02d', pd.YYYY, pd.MM, pd.target_day)
                ))
            WHEN pd.day_type = 'Friday' THEN 
                (SELECT COUNT(*) - 1 FROM (
                    WITH RECURSIVE split(idx, value, rest) AS (
                        SELECT 0, 
                               substr(pd.fridays, 1, instr(pd.fridays || ',', ',') - 1),
                               substr(pd.fridays, instr(pd.fridays || ',', ',') + 1)
                        UNION ALL
                        SELECT idx + 1,
                               substr(rest, 1, instr(rest || ',', ',') - 1),
                               CASE WHEN instr(rest, ',') > 0 THEN substr(rest, instr(rest, ',') + 1) ELSE '' END
                        FROM split WHERE rest <> ''
                    )
                    SELECT idx FROM split WHERE value <= printf('%04d%02d%02d', pd.YYYY, pd.MM, pd.target_day)
                      AND value = printf('%04d%02d%02d', pd.YYYY, pd.MM, pd.target_day)
                ))
            ELSE NULL
        END AS attendance_index
    FROM parsed_dates pd
    WHERE pd.day_type IS NOT NULL
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
    :target_date AS "Attendance Date",
    CASE 
        WHEN dp.day_type = 'Thursday' THEN
            CASE 
                WHEN substr(a.thursdays || ',', 
                           (SELECT MAX(0, MIN(dp.attendance_index * 2, length(a.thursdays))) FROM date_position WHERE id = dp.id) + 1, 
                           1) = '1' THEN 'Present'
                ELSE 'Absent'
            END
        WHEN dp.day_type = 'Friday' THEN
            CASE 
                WHEN substr(a.fridays || ',', 
                           (SELECT MAX(0, MIN(dp.attendance_index * 2, length(a.fridays))) FROM date_position WHERE id = dp.id) + 1, 
                           1) = '1' THEN 'Present'
                ELSE 'Absent'
            END
        ELSE 'N/A'
    END AS "Attendance Status"
FROM User u
JOIN Attendance a ON u.id = a.user_id
JOIN date_position dp ON a.MYTF_id = dp.id
WHERE u.active = 1
  AND (u.play_thursdays = 1 OR u.play_fridays = 1)
ORDER BY 
    u.last COLLATE NOCASE,
    u.first COLLATE NOCASE,
    CASE 
        WHEN u.prefer_email = 1 THEN 1
        WHEN u.prefer_text = 1 THEN 2
        WHEN u.prefer_phone = 1 THEN 3
        ELSE 4
    END;