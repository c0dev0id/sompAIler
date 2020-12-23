PRAGMA foreign_keys=ON;

CREATE table "user" (
	ROWID int primary key,
	name CHAR,
 	password VARCHAR,
 	last_password_match DATETIME,
 	expires_not_before DATETIME,
	constraint unique_username UNIQUE(name)
);

CREATE table worker (
	id int primary key,
	userid int default null references user(ROWID) on delete set null,
	given_resources int,
	used_resources int default 0,
	taken_times int,
	constraint unique_owner UNIQUE(userid)
);

CREATE VIEW stake AS
	SELECT NULL as owner, NULL as has_time, assigned_to_worker
	  FROM worker
	  WHERE userid IS NULL
        UNION SELECT
                u.ROWID,
        	(strftime('%s', expires_not_before)
        	-strftime('%s', datetime('now')))/3600.0,
        	w.id
          FROM "user" u
            LEFT OUTER JOIN  worker w on w.userid=u.ROWID
          WHERE expires_not_before < datetime('now')
        UNION SELECT
        	u.ROWID,
        	CASE strftime(
        	  '%s', datetime(u.last_password_match, '1 HOUR')
                ) >= strftime('%s', datetime('now'))
                  WHEN 1 THEN MIN(1, (
                      strftime('%s', u.expires_not_before)
                      - strftime('%s', datetime('now'))
                      )/3600.0)-1
                  WHEN 0 THEN NULL
		END,
        	w.id
          FROM "user" u
            LEFT OUTER JOIN  worker w on w.userid=u.ROWID
          WHERE expires_not_before >= datetime('now')
	;

create view workers as select * from worker;
create trigger assign_worker
    instead of insert on workers
begin
update worker set userid=NEW.userid, used_resources=0
    where id=(
	SELECT	assigned_to_worker
	FROM	stake s1
	  LEFT OUTER JOIN
		"user" u ON u.userid=s1.user
	WHERE   s1.has_time < (
		    SELECT has_time
		    FROM stake s2 WHERE "user"=NEW.userid
		)
	   OR   s1.has_time IS NULL
	ORDER   BY u.expires_not_before ASC
	LIMIT   1
    );
end
;

create trigger update_worker
    after update on worker
    when NEW.used_resources > OLD.used_resources
-- This trigger ensures that user has some time to re-use
-- samples that have been generated using time and cpu resources.
begin
    update "user" set expires_not_before=max(
       expires_not_before,
       datetime('now',
	   cast(min(1,
	       ( NEW.used_resources - OLD.used_resources )
	       * NEW.taken_times
	       / NEW.used_resources
	   ) * 3600 as int) || ' SECONDS'
       )
    );
end
;
