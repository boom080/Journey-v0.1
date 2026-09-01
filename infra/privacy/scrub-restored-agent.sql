-- Only on an isolated restore candidate. Never run on the live database.
-- Discard ALL old Agent state instead of relying on a deletion ledger that
-- could itself have been rolled back by the same backup.
BEGIN;
LOCK TABLE public.users IN ACCESS EXCLUSIVE MODE;
DELETE FROM public.agent_tool_runs;
DELETE FROM public.agent_confirmations;
DELETE FROM public.agent_runs;
DELETE FROM public.agent_threads;
DO $$ BEGIN
  IF to_regclass('public.agent_consents') IS NOT NULL THEN
    DELETE FROM public.agent_consents;
  END IF;
END $$;
DELETE FROM public.idempotency_keys WHERE path LIKE '/api/v1/agent/%';
DELETE FROM public.audit_events
WHERE resource_type IN ('agent', 'agent_run', 'agent_thread', 'agent_consent');
UPDATE public.auth_sessions SET revoked_at = now() WHERE revoked_at IS NULL;
COMMIT;
