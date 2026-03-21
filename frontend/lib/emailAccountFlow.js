export async function createEmailAccountFlow(input, deps) {
  try {
    await deps.create(input);
    await deps.reload();
    return { ok: true, error: null };
  } catch (error) {
    return { ok: false, error: String(error) };
  }
}
