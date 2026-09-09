# How I used AI in this project

I used Claude while building this. I'm writing it down properly because I think how someone uses
AI is part of how they should be judged now, and because "AI-assisted" on its own sounds like an
excuse.

## Where it helped

**Writing the data generator.** I decided the business logic — COD leads to more returns, longer
distance means higher shipping, the free-delivery limit creates a gap, and one courier should get
most of the hard routes so that the obvious reading of the data is wrong. Claude wrote the numpy
code. I picked every number and wrote them all down in `ASSUMPTIONS.md`.

**Code syntax.** Things like `np.select`, the `pd.cut` band edges, `format='mixed'` for the dates,
and the nested `CASE WHEN` in the SQL view. I know what each of them does. I didn't know all the
exact syntax, and looking it up in a chat is not really different from looking it up in the docs.

**Arguing against me.** This was the most useful part. After I reached a conclusion, I'd ask for
the case against it.

That's how the courier finding happened. My first read was "BharatShip is underperforming, we
should renegotiate." When I asked for the counter-argument, it was: what else is different between
these couriers apart from the courier? I checked the route mix, found BharatShip runs 38.5% of its
volume in tier 3 against SwiftLogix's 3.5%, and the whole gap disappeared once I compared them
inside the same zone.

That turned a wrong recommendation into a right one, and it gave me the strongest thing in the
project — a recommendation to do nothing.

**Structure.** Folder layout, README outline, dashboard spec format.

## Where it didn't decide anything

**The question.** "Which orders lose money and what one rule change fixes it" is something I chose
because it forces a decision. "Analyse the sales data" wouldn't have.

**The metric.** Contribution margin instead of gross margin (which sits above shipping and hides
the whole problem) and instead of net profit (which needs a fixed-cost split I couldn't defend).
This choice decides whether the project finds anything at all.

**Every assumption.** The 15% return write-off, the 35% switch rate, the 75% fee retention, the
₹499 and ₹699 band edges. On the write-off I deliberately picked the value that makes my own
recommendation harder to justify, because picking the flattering number is how you fool yourself.

**Deciding to compare within zones.** This is the core of the project and it changed both of my
obvious conclusions. Nothing prompted it except knowing that COD is more common outside metros,
which meant "COD orders" and "tier-3 orders" were partly the same orders.

**Recommending no courier action.** Once I'd built the courier analysis there was a pull to make it
produce something. Saying "no action needed" is less impressive and more correct.

**Every "so what".** A tool can produce a table. Deciding that the table means we should gate COD
by pincode rather than ban it is a judgement about this specific business.

## How I checked instead of trusting

**I wrote it twice.** The analysis exists in pandas (`analysis.py`, the notebook) and in SQL (`sql/`),
written separately. Both give 39,355 rows, ₹32,65,824 contribution margin and 11,169 loss-making
orders. If something had been wrong in one of them, the comparison would have caught it.

It did catch one. I'd been putting orders into value bands using revenue instead of order value.
Returned orders have zero revenue, so every single return was landing in the "under ₹300" bucket.
That quietly ruined the value-band analysis until the two versions disagreed.

**I checked a sample by hand.** I rebuilt the margin formula in Excel for 500 rows and matched it
against the code before trusting any total.

**I tested the assumptions instead of accepting them.** That's how I know the first recommendation
still makes money even if nobody switches to prepaid — the avoided losses don't depend on anyone
switching.

## What I'd say if asked

AI made me faster at the parts that were never the hard part. The hard parts were deciding what to
ask, picking a metric that would actually show something, noticing two things were mixed up, and
being willing to say "don't change anything" about the couriers. Those were mine and I can walk
through any of them without notes.

I'd rather be asked hard questions about this than have someone assume I couldn't answer them.
