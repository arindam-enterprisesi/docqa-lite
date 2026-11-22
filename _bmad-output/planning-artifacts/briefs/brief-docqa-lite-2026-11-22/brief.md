---
title: "Product Brief: docqa-lite"
status: final
created: 2026-11-22
updated: 2026-11-22
---

# Product Brief: docqa-lite

> Items tagged `[ASSUMPTION]` were inferred by the facilitator, not confirmed by the author. Review and correct them.

## Executive Summary

docqa-lite is a small document library with search. People upload Markdown or plain-text documents, browse them, and find the right one by typing a question in plain words. Results come back ranked, each with a relevance score and a short snippet showing why it matched.

It is built as a deliberately tiny service for an AI-autonomous software delivery training session: small enough to build end to end in one sitting, real enough that its behavior can be specified and tested. `[ASSUMPTION]` The brief is written as for a real product, but the stakes are those of a training exercise, so it makes no market claims.

## The Problem

`[ASSUMPTION]` A new employee needs a fact such as "how many days of annual leave do I get, and can I carry them over?" The answer lives in one of several policy documents, and they don't know which. Today they open files one by one, use Ctrl+F in each, or interrupt a manager or HR. That costs the asker minutes and costs someone else an interruption, repeated for every policy question across the company.

The sample corpus (expense, IT security, leave, onboarding and travel policies) mirrors this scenario.

## The Solution

A service where anyone can type a short query and get the best-matching documents, ranked, with a score and a snippet, instead of hunting through files. Content owners can add a new document and have it searchable on the very next request. Anyone can list the library and read a document in full.

Search is keyword-based (TF-IDF) with no AI model, so results are fast and identical for identical input.

## What Makes This Different

Not much, and that is the point. Shared drives and Ctrl+F already exist, and larger tools already do semantic search. docqa-lite's edge is narrowness:

- **Deterministic:** the same query over the same library always gives the same ranked results, so behavior can be fully tested.
- **No AI service dependency:** no API key and no per-query cost.
- **Small enough to understand end to end.**

`[ASSUMPTION]` There is no claimed moat. The value is a clear, testable foundation, not a competitive position.

## Who This Serves

- **Primary: the searcher.** `[ASSUMPTION]` An employee who needs a specific policy answer quickly and doesn't know which document holds it. Success means finding the right document in one query.
- **Secondary: the content owner.** `[ASSUMPTION]` Someone in HR, IT or finance who adds or refreshes documents. Success means the new document is findable immediately, with no re-indexing step.

## Success Criteria

Drawn from the feature spec:

- After start-up, all 5 sample documents are listable and searchable with zero manual steps.
- For each sample document, a query using a distinctive phrase returns it as the top result (5 of 5).
- A newly uploaded document is searchable on the very next request.
- Search over up to 1,000 documents returns in under 1 second.
- All invalid uploads and queries are rejected with a clear reason, and none cause a server error.
- The same query over the same library returns identical results and scores every time.

`[ASSUMPTION]` No adoption or business metrics apply, since this is a training exercise.

## Scope

**In (first version):**
- Upload one `.md`, `.markdown` or `.txt` file, up to 1 MB.
- List documents, and fetch one by id.
- Search with a text query, returning the top k results (default 5, maximum 20) with score and snippet.
- Load the five sample documents automatically at start-up.

**Out:**
- Authentication, authorization and per-user libraries.
- PDF and other binary formats.
- AI-generated answers or summaries.
- Updating and deleting documents.
- Persistence across restarts. Uploads are held in memory only.

## Vision

`[ASSUMPTION]` If it earned further investment, the natural path is persistent storage, update and delete, access control, more file types, and eventually semantic search and generated answers, each added behind the same tested interface. None of this is planned for the first version.

## Open Questions

- Who is the real primary user, and what do they do today instead? Both are inferred and unconfirmed.
