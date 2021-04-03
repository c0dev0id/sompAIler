PRAGMA foreign_keys=ON;

CREATE TABLE "user" (
    ROWID int primary key,
    name CHAR,
     password VARCHAR,
     last_password_match DATETIME DEFAULT CURRENT_TIMESTAMP,
        needs_worker_since DATETIME,
    tried_times INT,
     expires_not_before DATETIME,
    constraint unique_username UNIQUE(name)
);

CREATE TABLE worker (
    id INT primary key,
    userid INT default null REFERENCES user(ROWID) ON DELETE SET NULL,
    given_resources INT,
    used_resources INT DEFAULT 0,
    taken_times INT,
    CONSTRAINT unique_owner UNIQUE(userid)
);

CREATE VIEW stake AS
    SELECT ROW_NUMBER() OVER(ORDER BY has_time ASC) AS time_rank, *
    FROM (
        SELECT NULL AS userid, NULL AS has_time, id AS assigned_to_worker
          FROM worker
          WHERE userid IS NULL
            UNION SELECT
                u.ROWID,
                (strftime('%s', expires_not_before)
                -strftime('%s', 'now'))/3600.0,
                w.id
              FROM "user" u
                LEFT OUTER JOIN worker w ON w.userid=u.ROWID
              WHERE expires_not_before < datetime('now')
            UNION SELECT
                u.ROWID,
                CASE WHEN strftime(
                  '%s', u.last_password_match, '1 HOUR'
                      ) >= strftime('%s', 'now')
                        THEN MIN(1, (
                            strftime('%s', u.expires_not_before)
                            - strftime('%s', 'now')
                            )/3600.0)-1
                  ELSE NULL
                END,
                w.id
              FROM "user" u
                LEFT OUTER JOIN  worker w ON w.userid=u.ROWID
              WHERE expires_not_before >= datetime('now')
    );

CREATE VIEW waiting_users AS
    SELECT ROW_NUMBER() OVER(
        ORDER BY MIN(1, tried_times
        * (strftime('%s', 'now')
	  - strftime('%s', last_password_match)
          )
        / (strftime('%s', last_password_match)
	  - strftime('%s', needs_worker_since)
          )
        ) DESC) AS wait_rank, ROWID AS userid
    FROM "user"
        WHERE tried_times>0
    ;

CREATE VIEW workers_v as select * FROM worker;
CREATE TRIGGER assign_worker
    INSTEAD OF INSERT ON workers_v
BEGIN
UPDATE worker SET userid=NEW.userid, used_resources=0
    WHERE id=(
    SELECT	assigned_to_worker
    FROM	stake s1
      LEFT OUTER JOIN "user" u ON u.ROWID=s1.userid
      JOIN waiting_users wu ON s1.time_rank=wu.wait_rank
    WHERE  (s1.has_time < (
            SELECT has_time
            FROM stake s2 WHERE s2.userid=NEW.userid
        ) OR s1.has_time IS NULL)
      AND  wu.userid=u.ROWID
    );
END;

CREATE TRIGGER update_lpm_request_worker
    BEFORE UPDATE OF last_password_match ON "user"
    WHEN NEW.last_password_match > OLD.last_password_match
BEGIN
    UPDATE "user"
      SET tried_times=tried_times+((
		-- Only count one try in a minute
		strftime('%s', NEW.last_password_match)
	      - strftime('%s', OLD.last_password_match)
	    ) > 60)
          needs_worker_since=ifnull(needs_worker_since, datetime('now'))
      WHERE ROWID=OLD.ROWID;
    INSERT OR IGNORE INTO workers_v (userid) VALUES(OLD.ROWID);
END;

CREATE TRIGGER resets_on_successful_worker_assignment
    AFTER UPDATE OF last_password_match ON "user"
    WHEN OLD.ROWID IN (SELECT userid FROM worker)
BEGIN
    UPDATE "user"
      SET tried_times=0, needs_worker_since=NULL
      WHERE ROWID=OLD.ROWID;
END;

CREATE TRIGGER update_worker
    AFTER UPDATE ON worker
    WHEN NEW.used_resources > OLD.used_resources
-- This trigger grants the user some more time to re-use
-- samples that have been generated using time and cpu resources.
BEGIN
    UPDATE "user" SET expires_not_before=max(
       expires_not_before,
       datetime('now',
       CAST(min(1,
           ( NEW.used_resources - OLD.used_resources )
           * NEW.taken_times
           / NEW.used_resources
       ) * 3600 AS INT) || ' SECONDS'
       )
    );
END;
