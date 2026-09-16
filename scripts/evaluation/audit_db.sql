-- Run only on the synthetic journey_test database at localhost port 55439.
SELECT json_build_object(
 'total_food_rows',(SELECT count(*) FROM food_records),
 'duplicate_groups',(SELECT count(*) FROM (
   SELECT user_id,recorded_at,name,energy_kcal,count(*) FROM food_records
   GROUP BY user_id,recorded_at,name,energy_kcal HAVING count(*)>1) d),
 'excess_duplicate_rows',(SELECT coalesce(sum(n-1),0) FROM (
   SELECT count(*) n FROM food_records
   GROUP BY user_id,recorded_at,name,energy_kcal HAVING count(*)>1) d)
);
