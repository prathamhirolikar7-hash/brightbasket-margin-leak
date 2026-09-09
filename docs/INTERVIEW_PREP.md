# Notes for defending this project

These are my own notes. The point isn't to memorise the answers — memorised answers sound
memorised, and the follow-up question breaks them. I read one, close the file, and say it in my own
words. If I can't, that's the bit I don't understand yet.

---

## The short version

For "tell me about a project you've worked on". Say it and stop.

> I looked at a D2C brand where orders had grown 30% but profit was flat. I worked out the profit on
> every individual order — revenue minus product cost, shipping, returns and payment fees — and
> found 28% of orders were losing money. About ₹11.5 lakh, which was a quarter of everything the
> profitable orders made.
>
> The obvious answer was that cash on delivery was the problem, because COD orders made ₹60 each and
> prepaid made ₹114. But COD is much more common outside metros, so I compared them within each city
> tier separately. COD in metros actually makes ₹92 an order. The real problem was COD plus tier-3
> cities plus small orders — about 8% of volume with a 17% return rate.
>
> So I recommended blocking COD by pincode instead of banning it, plus raising the free-delivery
> limit. Together about ₹5.7 lakh a year. And I recommended *not* changing courier, which was the
> other thing the data seemed to suggest — the worst-looking courier just had the harder routes.

---

## About the data

### "This data is made up. Doesn't that make the project pointless?"

Hardest question I'll get. Don't get defensive.

> It means the findings aren't a discovery about a real company, and I'd never claim they were. What
> it shows is the method.
>
> I looked for real data first. The problem is that order-level product cost, shipping cost and
> return status together is exactly what no company publishes — that's their unit economics. So I
> had two options: pick a weaker question that public data could answer, or build realistic data for
> the question that actually matters. I picked the second and left the generator open in the repo
> with every number written down.
>
> I'd rather be upfront about made-up data than quietly use a Kaggle file with no background and
> call it real. The actual work — the margin definition, the checks, the sensitivity testing — is
> what I'd do on your data on day one.

**If pushed: "but you built in the answer you found":**

> Partly, yes. Data with no pattern has nothing to find. But I also built in two traps I then had to
> catch — COD mixed up with geography, and a courier that looks bad because of route mix. I didn't
> have to catch either. The value is the habit of checking whether the obvious answer survives, and
> that transfers.

### "Why 40,000 orders? Why one year?"

> 40,000 means the smallest group I care about — tier-3 COD — still has 4,600 orders, so the
> averages aren't noise. One year stops me pretending to analyse seasonality I have no basis for.

### "Why four tables instead of one file?"

> Because that's how it arrives in real life. Orders come from the order system, shipping costs from
> the courier's monthly bill, the pincode-to-zone mapping is a reference table, customers from the
> CRM. Doing it that way meant handling joins properly, which is where the real mistakes happen.

---

## About cleaning

### "You removed 602 rows. How do you know that didn't skew the result?"

Have the number ready. This one separates people.

> I checked before removing them. The removed rows were 53% COD. The rows I kept were 57% COD. Close
> enough that it doesn't affect the payment-mode conclusion, which the whole project rests on.
>
> If it had come back 90% COD, removing them would have deleted exactly the evidence I needed. I'd
> have had to work out the zone from the city field instead. The check takes thirty seconds and it's
> the difference between "I dropped 1.5% of rows" and "I dropped 1.5% and here's why that's safe".

### "Why fix the negative discounts instead of deleting those rows?"

> Because a negative discount isn't a broken row, it's one wrong field. The order is real — valid
> customer, date, pincode, product cost. Deleting it throws away four good fields to fix one. A
> discount is an amount; the minus sign came from a refund entered in the wrong column. I made it
> positive and added a flag so anyone can see which 120 rows I changed.

### "Why not use errors='coerce' on the dates?"

> Because it silently turns anything it can't read into a blank. About 900 rows were in DD-MM-YYYY,
> so I'd have wiped 900 real dates and never known.
>
> My rule is not to use an error-hiding setting until I know what it's hiding. `coerce` is fine
> after you've looked at the failures, never before.

### "The 140 cancelled orders with shipping charges — why is that a finding?"

> Because a cancelled order was never sent, so there's nothing to charge for. That's the courier
> billing us for work they didn't do. Small money, but if it's happening in this sample it's
> probably happening every month. I'd raise it with ops separately. Part of the job is noticing
> things you weren't asked to look for.

### "Why keep cancelled orders at all?"

> Because the cancellation rate is information — if it spiked in one group that would matter. They
> sit in the table with zero revenue and zero cost so they don't distort totals.
>
> One honest thing: keeping them drags my per-order averages down slightly, maybe 3%. It doesn't
> change the ranking of the groups, which is what the decision depends on, so I left them. If I were
> being extra careful I'd have shown it both ways.

Saying that last bit unprompted is worth more than a clean answer.

---

## About the metric

### "Why contribution margin? Why not gross margin or actual profit?"

The centre of the project. Know it properly.

> Gross margin is revenue minus product cost. Shipping and returns sit below that line, so on gross
> margin every order in this data looks healthy. The metric would have hidden the whole problem.
>
> Net profit has the opposite issue. It needs fixed costs — salaries, rent, brand marketing — that
> don't change when one more order comes in. To split them per order I'd need a rule, and any rule
> I picked would be made up. I'd be making small orders look worse for reasons that have nothing to
> do with the decision.
>
> Contribution margin is revenue minus every cost that only exists because this order happened. My
> question is "should we keep taking orders like this one?" For that, only the costs that appear and
> disappear with the order matter. If it's negative, every extra order makes the company poorer.

### "Why only 15% of product cost on a return?"

> Because the goods come back to the warehouse and get sold again. We haven't lost the stock, we've
> lost the damaged and expired share, and we've paid shipping twice.
>
> Charging the full cost would roughly double the apparent loss and make my recommendation look
> better than it is. I checked what happens if I'm wrong: at 30%, tier-3 COD goes from −₹4 to about
> −₹19, so the case gets stronger. At 5% it goes slightly positive and the case weakens a lot.
>
> So it matters, and I picked the cautious end on purpose. Choosing the number that makes your own
> argument harder is how you avoid fooling yourself.

### "2% for prepaid but a flat ₹25 for COD — isn't that inconsistent?"

> It's different because the real costs are different, and that's part of the story. A gateway takes
> a percentage, so it grows with order size. COD handling is a flat fee for collecting cash — same
> whether the order is ₹300 or ₹3,000.
>
> So COD is relatively cheaper on big orders and more expensive on small ones, which fits the
> order-size finding. If I'd made both percentages I'd have smoothed out a real effect.

### "Why put the formula in a SQL view?"

> One place to change it. If I paste it into six queries and later change the COD fee from ₹25 to
> ₹30, five go stale and my dashboard quietly disagrees with my SQL. It also means someone can read
> one file and know exactly how I define the number.

---

## The two findings that changed my answer

### "Walk me through why you didn't just recommend restricting COD."

Best story I have. Tell it as a story.

> My first cut was payment mode on its own: COD ₹60 an order, prepaid ₹114. That looks settled. The
> obvious answer is restrict COD.
>
> But COD isn't spread evenly. It's 46% of orders in metros and 79% in tier 3, because fewer people
> there pay online. So "COD orders" is partly just another name for "tier-3 orders", and tier 3 is
> expensive for reasons that have nothing to do with how the customer pays.
>
> So I compared them within each zone. COD in metros makes ₹92 an order. That's profitable, and it
> brings in people who won't pay upfront. COD is worse than prepaid everywhere, but it only goes
> below zero in tier 3, where it hits a 16% return rate and expensive shipping.
>
> That's why my recommendation is geographic instead of about payment. Banning COD everywhere would
> have destroyed about ₹9 lakh of good metro profit to fix an ₹18,000 problem.

**Likely follow-up: "But COD is worse in every zone. Wasn't the simple answer right?"**

> Worse, yes, in all three. But the decision isn't "is COD worse", it's "should we take this order".
> That depends on the sign, not the gap. Metro COD still makes ₹92 — refusing it doesn't turn those
> customers into prepaid customers, it just loses the order. Tier 3 is the only place it crosses
> zero.
>
> The gap widening from ₹30 in metro to ₹77 in tier 3 also tells me COD and distance don't just add
> up, they multiply. The return rate compounds, and return costs scale with distance.

### "The courier thing — walk me through it."

> Raw numbers say BharatShip makes ₹56 an order and SwiftLogix ₹96. Looks like a bad partner.
>
> But BharatShip runs 38.5% of its volume in tier 3 and SwiftLogix runs 3.5%. They're not worse,
> they get the hard routes, usually because they're the only ones who go there.
>
> Compared inside the same zone, all three are within a few rupees. In tier 3 it's ₹13.2 for
> BharatShip and ₹13.5 for SwiftLogix. That's a tie.
>
> So my recommendation is do nothing. Switching partners would have taken weeks and changed nothing,
> because the cost driver is where we ship, not who ships it.

**If asked what it's called:** Simpson's paradox — where a pattern flips once you split by something
hidden. But add: *the name matters less than the habit. What I ask about any two groups I'm
comparing is: what else is different between them?*

**Also be ready for:** ZipEx shows ₹7.4 in tier 3 against the other two at ₹13.2 and ₹13.5. That's a
real gap. But ZipEx only runs 6.3% of its volume there, so the sample is small and the number noisy
— and even if real, it's rounding error next to ₹5.7 lakh. Knowing when a difference is too small to
act on is part of the job.

### "How did you pick those order-size bands?"

> The edges are at 300, 500, 700 and 1000 so one edge sits exactly on the ₹499 free-delivery line.
> With even ₹250 buckets the gap would have been split across two buckets and I'd never have seen
> it. Bucket edges should sit where the decision is, not on round numbers.

### "Why did you look at the free-delivery rule? Nobody asked you to."

> Because the numbers didn't add up. Tier 3 explained part of the loss, but tier 3 is only 15% of
> orders and 28% were losing money. Something else was bleeding.
>
> So I asked what else could make a normal order lose money, and the obvious suspect was a rule we
> set ourselves. Orders of ₹500–699 make ₹53 each and ₹700–999 make ₹182. That's a big jump for
> orders barely different in size. That's not customers, that's our threshold.

### "28% of orders lose money. Is that a problem or normal?"

> Some of it is normal. Any business with a flat delivery fee loses money on its smallest orders, and
> that's fine if those orders bring in customers who come back.
>
> What makes it a problem is the size and concentration. ₹11.5 lakh, a quarter of what the good
> orders make, sitting in identifiable groups rather than scattered. Concentrated means fixable.
>
> The honest gap is that I have no repeat-purchase data, so I can't say whether those losing orders
> are buying future profitable customers. That's the biggest hole in the analysis.

---

## About the recommendation

### "You're giving up ₹9.6 lakh of sales to gain ₹2 lakh of profit. Justify that."

Expect this. Strongest challenge to the whole thing.

> Because that ₹9.6 lakh of sales loses money. Every rupee makes the company slightly poorer. Sales
> you lose money on isn't an asset — you'd be better off without it.
>
> That said, I'd present it as a trade-off, not a slam dunk. If the company is raising money on sales
> growth, ₹9.6 lakh of top line might be worth more short-term than ₹2 lakh of profit, and that's a
> management call, not mine. And I don't have lifetime value data, so I can't rule out that some of
> those customers become profitable later.
>
> Which is why what I'd actually propose is a two-week test on five pincodes rather than a rollout.
> That answers both questions with real data instead of my guesses.

Saying "that's above my level" is a strength here, not a weakness.

### "Where does 35% come from, and what if it's wrong?"

> A judgement, not a measurement. Published Indian figures for COD-to-prepaid nudges sit between 25%
> and 45%, and I took the middle, leaning pessimistic.
>
> The important thing is the recommendation doesn't depend on it. The ₹1.82 lakh of avoided losses
> happens the moment we stop taking the loss-making order — nobody has to switch for that. Switching
> only affects the size of the gain, never whether there is one. It makes money even at 0%.
>
> If I could only defend one number here, it's that one, because it means I'm not asking anyone to
> bet on my guess.

### "Which of your assumptions is weakest?"

Be specific. "None, really" loses the room.

> The 75% retention on the delivery fee change, and it's not close. Unlike the other one there's no
> avoided-loss floor under it. If customers drop out at 50% instead of 25%, that falls from ₹3.74
> lakh to ₹2.49 lakh. Still positive, much less.
>
> It cuts the other way too: some customers will add an item to get over ₹699 instead of paying ₹49.
> That would make the real number higher and lift average order value, which I haven't counted. I
> don't know which effect wins, and I'd want to test it.

### "If you had two more weeks, what would you do?"

> Three things. First, a repeat-purchase analysis — my biggest blind spot is that this is order by
> order, so I can't see whether a blocked customer would have become profitable later. Second, design
> the test properly: pick the pincodes, work out how many orders I need, decide when to stop before
> starting. Third, check whether returns are concentrated in specific pincodes rather than all of
> tier 3. If it's twenty pincodes instead of the whole zone, the rule gets much more targeted and we
> give up far less sales.

---

## Technical follow-ups

### "Why LEFT JOIN and not INNER JOIN?"

> So a join can't quietly delete orders. With INNER JOIN, any order whose pincode isn't in the
> reference table vanishes and I'd never know — that's how people lose 2% of revenue without
> noticing. With LEFT JOIN I see them as blanks and remove them on purpose, with a count I can
> report. I keep the orders table on the left throughout for the same reason.

### "Your SQL says 119 negative discounts, your notebook says 120. Which is wrong?"

Someone thorough will spot this. It isn't an error.

> Neither. The notebook counts them in the raw file, before removing duplicates. The SQL fixes them
> after, and one of those rows was a duplicate that got removed first. Same for the shipping charges
> — 140 in SQL, 134 in the notebook, because the notebook counts after also removing rows with no
> pincode.
>
> It's an ordering difference. I checked when the numbers didn't match, which is exactly why I wrote
> the analysis in both SQL and pandas. That comparison caught a real bug: I'd been putting orders
> into size bands using revenue instead of order value, and returned orders have zero revenue, so
> every return was landing in the smallest bucket. It quietly ruined that analysis until the two
> versions disagreed.

Worth a lot. Shows I built a check and it worked.

### "How do you know your Excel dashboard is right?"

> I cross-checked it against the Python and SQL, and it caught something. My PivotTable was showing
> stale numbers from an old cache — it said tier 2 was losing money, which would have contradicted my
> own recommendation. No error message. I only found it because the pivot disagreed with the sheet
> next to it.
>
> Same with my sensitivity table. Zero errors, completely wrong — I'd pointed part of the formula at
> the wrong cell. It showed ₹202,054 where the model above it said ₹570,298.
>
> A spreadsheet with no error messages isn't the same as a spreadsheet with right answers.

### "What would change if this were 50 million rows?"

> pandas breaks — that won't fit in memory on a laptop. I'd push the grouping into the database and
> pull out only summaries, which is one reason the margin formula is a SQL view: it already runs
> where the data is. For the dashboard I'd load a pre-summarised extract, which means deciding the
> breakdowns up front.
>
> I should be straight that I haven't worked at that scale. I know what the constraint is and roughly
> what the answer looks like, and I'd expect to learn the details on the job.

Never claim experience I don't have. "Here's how I'd think about it, and here's where my knowledge
stops" is a good answer. A confident wrong one isn't.

---

## The AI question

### "You used AI. How much of this is actually yours?"

Answer directly. Don't over-explain.

> The syntax was AI-assisted. The thinking was mine and I can show you which is which.
>
> I picked the question, and I picked contribution margin over gross margin — the decision that
> determines whether the project finds anything, because gross margin sits above shipping and hides
> the whole problem. I set every assumption, including deliberately picking the return write-off that
> makes my own case harder.
>
> The most useful thing I used it for was arguing against me. After I concluded BharatShip was
> underperforming, I asked for the case against, and the reply was "what else is different between
> these couriers?" That's what made me check route mix and reverse my recommendation.
>
> And I checked rather than trusted. The analysis exists in both SQL and pandas, written separately,
> and they agree to the rupee. That comparison caught a real bug in my own logic.

### "Could you have done it without AI?"

> Slower, and the code would be uglier. But yes — nothing here is beyond what I can write. Some
> syntax I'd have had to look up, which is what I was doing anyway.
>
> What I wouldn't give up is the argument-against-me part. Having something push back when I'm most
> confident is useful, and I don't think that's a crutch — it's what a good senior analyst does in a
> review.

---

## Traps

**"Your numbers are wrong, I calculated X."** → *"Let me check — how did you get there?"* Then
actually check. Don't defend a number I haven't verified, don't fold on one I have. If they're
right, say so straight away. Handling a mistake well reads better than being right.

**"This is pretty basic. Have you done machine learning?"** → *"Not on this project, it didn't need
it. The question was where profit is leaking, which is a segmentation and unit economics problem. A
churn model would have been more impressive and less useful."*

**"Why you over someone with a CS degree?"** → Don't run down the comparison. *"I'd point at the
courier finding. The technical work there was a pivot table. What mattered was asking whether the
obvious answer was right, and being willing to say do nothing."*

**Silence after my answer.** They're testing whether I fill it. Stop talking. If I must, ask *"would
you like me to go deeper on any of that?"*

**A question I can't answer.** *"I don't know. My guess would be X, but I'd want to check before
saying that with confidence."* Never make something up.

---

## Can I do these without notes?

- [ ] Say the question and the decision it drives, in one sentence
- [ ] Explain contribution margin vs gross margin vs net profit
- [ ] Tell the COD story, including the ₹9 lakh mistake I avoided
- [ ] Tell the courier story and land on "do nothing"
- [ ] Name every assumption and say which is weakest, without pausing
- [ ] Explain why I removed 602 rows and how I know it was safe
- [ ] Justify giving up ₹9.6 lakh of sales
- [ ] Say what I'd do with two more weeks
- [ ] Answer the AI question in under 45 seconds without sounding defensive
- [ ] Explain something I got wrong and how I caught it

If I can do all ten out loud, the project is mine. If I can't do one, that's the bit to reread.
