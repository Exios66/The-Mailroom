import axios from 'axios'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { reviewApi } from '@/api/review'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle, XCircle, FileText, ChevronRight } from 'lucide-react'
import type { Document, ReviewResolution } from '@/types/api'

export default function ReviewPanel() {
  const { data: docs, isLoading, error } = useQuery({
    queryKey: ['review-queue'],
    queryFn: reviewApi.getReviewQueue,
    refetchInterval: 3000,
  })
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null)
  const [comment, setComment] = useState('')
  const [disposition, setDisposition] = useState<ReviewResolution['disposition']>('resume')
  const [extractedData, setExtractedData] = useState('')
  const queryClient = useQueryClient()

  const resolveMutation = useMutation({
    mutationFn: ({ doc, resolution }: { doc: Document; resolution: 'approved' | 'rejected' }) => {
      let extracted_data: Record<string, unknown> | undefined
      if (disposition === 'complete' && extractedData.trim()) {
        let parsed: unknown
        try { parsed = JSON.parse(extractedData) }
        catch { throw new Error('Complete needs valid extracted_data JSON.') }
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
          throw new Error('Complete needs an extracted_data JSON object.')
        }
        extracted_data = parsed as Record<string, unknown>
      }
      return reviewApi.resolve(doc, { resolution, comment, disposition, extracted_data })
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['review-queue'] })
      void queryClient.invalidateQueries({ queryKey: ['queue'] })
      setSelectedDoc(null)
      setComment('')
    },
  })

  const { data: preview } = useQuery({
    queryKey: ['preview', selectedDoc?.doc_id, selectedDoc?.trace_id],
    queryFn: () => reviewApi.source(selectedDoc!),
    enabled: !!selectedDoc,
  })

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground">Loading review queue…</div>
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Human Review Queue</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {docs?.length || 0} documents awaiting review (Langfuse + producer proxy)
        </p>
        {error ? (
          <p className="text-sm text-destructive mt-2">
            Review queue unavailable. Display stays Langfuse-only; resolve needs MAILROOM_PIPELINE_URL.
          </p>
        ) : null}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-2">
          {docs?.map((doc) => (
            <button
              type="button"
              key={doc.trace_id || doc.doc_id}
              onClick={() => {
                setSelectedDoc(doc)
                setDisposition(doc.stage === 'review' ? 'resume' : 'record')
                setComment('')
                setExtractedData('')
                resolveMutation.reset()
              }}
              disabled={resolveMutation.isPending}
              className={`w-full text-left p-4 rounded-lg border transition-all ${
                selectedDoc?.doc_id === doc.doc_id
                  ? 'border-primary bg-primary/5'
                  : 'border-border bg-card hover:border-muted-foreground/30'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">{doc.filename || doc.doc_id}</p>
                    <p className="text-xs text-muted-foreground">
                      {doc.doc_type} — {doc.review_reason || doc.verdict || 'needs review'}
                    </p>
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </div>
            </button>
          ))}
          {(!docs || docs.length === 0) && (
            <div className="text-center py-12 text-muted-foreground border border-dashed border-border rounded-lg">
              No documents in review queue
            </div>
          )}
        </div>

        {selectedDoc && (
          <div className="border border-border rounded-lg bg-card p-6 space-y-4">
            <div>
              <h3 className="font-medium">{selectedDoc.filename || selectedDoc.doc_id}</h3>
              <p className="text-sm text-muted-foreground">{selectedDoc.doc_type}</p>
              <Link
                to={`/audit/${selectedDoc.doc_id}`}
                className="text-xs text-muted-foreground underline"
              >
                Audit trail
              </Link>
            </div>

            <div className="border border-border rounded-md p-4 bg-background min-h-[160px] max-h-[320px] overflow-auto">
              {preview?.text ? (
                <pre className="text-xs whitespace-pre-wrap">{preview.text}</pre>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {preview?.error || 'No parked text (producer source / lookup fallback).'}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="review-disposition" className="text-sm font-medium">Disposition</label>
              <select
                id="review-disposition"
                disabled={resolveMutation.isPending}
                value={disposition}
                onChange={(e) => setDisposition(e.target.value as ReviewResolution['disposition'])}
                className="w-full mt-1 px-3 py-2 rounded-md border border-input bg-background text-sm"
              >
                <option value="resume" disabled={selectedDoc.stage !== 'review'}>resume</option>
                <option value="record">record</option>
                <option value="requeue">requeue</option>
                <option value="complete" disabled={selectedDoc.stage !== 'review'}>complete</option>
              </select>
            </div>

            {disposition === 'complete' && (
              <div>
                <label htmlFor="review-extracted-data" className="text-sm font-medium">Extracted data (JSON object)</label>
                <textarea
                  id="review-extracted-data"
                  value={extractedData}
                  onChange={(e) => setExtractedData(e.target.value)}
                  disabled={resolveMutation.isPending}
                  className="w-full mt-1 px-3 py-2 rounded-md border border-input bg-background text-sm font-mono"
                  rows={6}
                  placeholder='Leave blank to use the parked extraction'
                />
              </div>
            )}
            <div>
              <label htmlFor="review-comment" className="text-sm font-medium">Review comment</label>
              <textarea
                id="review-comment"
                disabled={resolveMutation.isPending}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                className="w-full mt-1 px-3 py-2 rounded-md border border-input bg-background text-sm"
                rows={3}
                placeholder="Optional notes forwarded to the producer"
              />
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => resolveMutation.mutate({ doc: selectedDoc, resolution: 'approved' })}
                disabled={resolveMutation.isPending}
                className="flex-1 flex items-center justify-center gap-2 py-2 rounded-md bg-emerald-600 text-white text-sm font-medium disabled:opacity-50"
              >
                <CheckCircle className="h-4 w-4" />
                Approve
              </button>
              <button
                type="button"
                onClick={() => resolveMutation.mutate({ doc: selectedDoc, resolution: 'rejected' })}
                disabled={resolveMutation.isPending || disposition === 'complete'}
                className="flex-1 flex items-center justify-center gap-2 py-2 rounded-md bg-red-600 text-white text-sm font-medium disabled:opacity-50"
              >
                <XCircle className="h-4 w-4" />
                Reject
              </button>
            </div>
            {resolveMutation.isError && (
              <p className="text-sm text-destructive">
                {axios.isAxiosError(resolveMutation.error)
                  ? String(resolveMutation.error.response?.data?.detail || resolveMutation.error.response?.data?.error || resolveMutation.error.message)
                  : resolveMutation.error.message}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
