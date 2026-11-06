import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { auditApi } from '@/api/audit'
import type { AuditEntry } from '@/types/api'
import { ShieldCheck, ShieldAlert, Link2 } from 'lucide-react'

// Producer rows use entry_id / event / entry_hash; id / action / hash are legacy aliases.
export function entryId(entry: AuditEntry, index: number): string {
  return String(entry.entry_id ?? entry.id ?? index)
}
export function entryEvent(entry: AuditEntry): string {
  return String(entry.event || entry.action || 'event')
}
export function entryHash(entry: AuditEntry): string {
  return String(entry.entry_hash || entry.hash || '—')
}

function detailText(detail: unknown): string {
  if (detail == null || detail === '') return ''
  if (typeof detail === 'string') return detail
  try {
    return JSON.stringify(detail)
  } catch {
    return String(detail)
  }
}

// Top-level rows in chain order; sub-rows and addenda (unified audit row) nest under parent_id.
export function nestEntries(entries: AuditEntry[]): { entry: AuditEntry; children: AuditEntry[] }[] {
  const ids = new Set(entries.map((e, i) => entryId(e, i)))
  const children = new Map<string, AuditEntry[]>()
  const roots: AuditEntry[] = []
  for (const entry of entries) {
    const parent = entry.parent_id ? String(entry.parent_id) : ''
    if (parent && ids.has(parent)) {
      children.set(parent, [...(children.get(parent) ?? []), entry])
    } else {
      roots.push(entry)
    }
  }
  return roots.map((entry) => ({ entry, children: children.get(entryId(entry, entries.indexOf(entry))) ?? [] }))
}

function EntryCard({ entry, index }: { entry: AuditEntry; index: number }) {
  const detail = detailText(entry.detail)
  return (
    <div className="border border-border rounded-lg p-4 bg-card">
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-sm font-medium">
          {entryEvent(entry)}
          {entry.kind && (
            <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">{entry.kind}</span>
          )}
        </span>
        <span className="text-xs text-muted-foreground">
          {entry.timestamp ? new Date(String(entry.timestamp)).toLocaleString() : ''}
        </span>
      </div>
      {entry.actor && <p className="text-xs text-muted-foreground mb-1">Actor: {String(entry.actor)}</p>}
      {detail && <p className="text-xs text-muted-foreground mb-1 break-words">{detail}</p>}
      <p className="text-xs text-muted-foreground font-mono break-all">
        <span className="text-foreground">Hash:</span> {entryHash(entry)}
      </p>
      <p className="text-xs text-muted-foreground font-mono break-all">
        <span className="text-foreground">Previous:</span> {String(entry.prev_hash || 'genesis')}
      </p>
      <p className="sr-only">Entry {entryId(entry, index)}</p>
    </div>
  )
}

export default function AuditChain() {
  const { docId } = useParams<{ docId: string }>()
  const { data, isLoading, error } = useQuery({
    queryKey: ['audit', docId],
    queryFn: () => auditApi.verifyChain(docId!),
    enabled: !!docId,
  })

  if (isLoading) return <div className="p-8 text-center text-muted-foreground">Verifying chain…</div>
  if (error || !data) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        No audit data — GET /api/review/audit needs MAILROOM_PIPELINE_URL.
      </div>
    )
  }

  const rows = nestEntries(data.entries)

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Audit Trail</h1>
        <p className="text-sm text-muted-foreground mt-1">Document: {docId}</p>
      </div>

      <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium ${
        data.chain_valid
          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
          : 'bg-red-50 text-red-700 border border-red-200'
      }`}
      >
        {data.chain_valid ? <ShieldCheck className="h-4 w-4" /> : <ShieldAlert className="h-4 w-4" />}
        {data.chain_valid ? 'Chain valid' : data.error || 'Chain invalid or unavailable'}
      </div>

      <ol className="space-y-0">
        {rows.map(({ entry, children }, i) => (
          <li key={entryId(entry, i)} className="relative pl-8 pb-6 last:pb-0">
            {i < rows.length - 1 && <div className="absolute left-3 top-6 bottom-0 w-px bg-border" />}
            <div className="absolute left-0 top-1 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
              <Link2 className="h-3 w-3 text-primary" />
            </div>
            <EntryCard entry={entry} index={i} />
            {children.length > 0 && (
              <ol className="mt-2 ml-4 space-y-2 border-l border-border pl-4">
                {children.map((child, j) => (
                  <li key={entryId(child, j)}>
                    <EntryCard entry={child} index={j} />
                  </li>
                ))}
              </ol>
            )}
          </li>
        ))}
        {rows.length === 0 && <p className="text-sm text-muted-foreground">Producer returned no hash-chain rows.</p>}
      </ol>
    </div>
  )
}
