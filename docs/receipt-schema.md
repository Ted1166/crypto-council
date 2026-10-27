# Receipt schema

A receipt is one `Case`, stored as JSON in SQLite and served by `GET /api/cases/{id}`. The Trial Room, the Case Board and the public receipt page all read this one object.

## Case

| Field | Meaning |
| --- | --- |
| id | Ten character hearing id |
| symbol | Token symbol under hearing |
| status | running, complete, failed or interrupted |
| model | Provider and model that argued the case |
| evidence | Every RYO tool call, in order, as ToolResult |
| arguments | Bull and bear opening and rebuttal arguments |
| verdict | The judge's current call |
| crossexams | Every interruption with before and after |
| error | Plain explanation when status is failed or interrupted |

## ToolResult

| Field | Meaning |
| --- | --- |
| id | E1, E2 and so on. Claims cite these |
| tool | RYO tool name |
| arguments | The arguments actually sent, after schema mapping |
| status | ok, unavailable or error |
| data | The tool's response, only when status is ok |
| error | Reason when status is not ok |
| fetched_at | When the data was retrieved |
| latency_ms | Round trip time |
| cached | True when served from the short cache |

Missing data stays missing. A tool that fails never carries placeholder data, and agents are told which tools are unavailable.

## Claim

A claim has text, the evidence ids it cites, and figures. Each figure is a label, a number and the evidence id it came from. A claim is removed before it reaches the receipt when:

- it cites no evidence, an id that does not exist, or evidence that was unavailable
- a figure is not found in the cited evidence
- a checkable number in its text, meaning a decimal, a percentage, a dollar amount, a k, M or B amount, or a number of 1,000 or more outside the years 1900 to 2100, is not found in the cited evidence

Removed claims are kept on the argument as `rejected`, with the reason, so the receipt shows what the agent got wrong.

## Verdict

direction is long, short or stand_aside. conviction is 0 to 100. The plan is computed in code, never by the model: entry is the reported price, stop is 1.5 ATR away and target is 3 ATR away, using the price and ATR(14) found in the evidence. If either is missing there is no plan and `plan_note` says why.

Conviction is capped at 60 when the safety check is unavailable, and at 20 when neither advocate produced a surviving claim.

## CrossExam

challenge, the planned tool calls, the ids of the new evidence, the answers under challenge, `verdict_before`, `verdict_after` and a `diff` with the direction change, conviction change and a one line summary. The Case Board ranks hearings by this diff.
