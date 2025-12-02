delete from tickets;

ALTER TABLE train_schedule
ADD COLUMN capacity INT NOT NULL DEFAULT 0;

ALTER TABLE tickets
ADD CONSTRAINT fk_tickets_schedule
FOREIGN KEY (schedule_id) REFERENCES train_schedule(schedule_id);

ALTER TABLE train_schedule
ADD COLUMN capacity INT NOT NULL DEFAULT 0;

DESC train_schedule;
-- verify there is a `capacity` INT column

UPDATE train_schedule
SET capacity = 300;  -- or different value per train
