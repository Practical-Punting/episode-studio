"""One golden card per library block, at its DECLARED MAXIMUM row count.

🔴 THE MAXIMUM IS THE POINT. A pacing budget is only interesting at the worst case: a
two-row `compare` fits inside 2.5s at any stagger anybody could choose, and a seven-row
ledger does not. Every card here therefore carries as many rows as its block allows, so
the contact sheets show the slowest build each block can produce rather than a
comfortable one.

The content is real Practical Punting material in shape and length — figures that read
like racing figures, labels the length of real labels — because a stagger that works on
"Row one / Row two" and fails on "A win strike of between 25 and 39 per cent from 10
starts or more" has not been tested.

⚠️ NOT TRACED, AND DELIBERATELY NOT AN EPISODE. These never reach a build: `render_card`
is called directly by the contact-sheet harness. Nothing here may be lifted into an
episode — a figure on a card must trace to that episode's own article.
"""

GOLDEN = {
 "stat": {"job": "anchor", "eyebrow": "The Number", "headline_display": "Most of<br>Them Lose",
          "content": {"figure": "60 Days+", "figure_sub": "Resuming from a spell",
                      "payoff": "Most will lose at their first run back.",
                      "note": "Measured across a full season of metropolitan racing."}},
 "statement": {"job": "anchor", "eyebrow": "Say It Plainly",
               "headline_display": "One Rule<br>Above All",
               "content": {"line": "Each of us has his or her own way of chucking out "
                                   "contenders, and giving our vote to others.",
                           "note": "The rest is detail."}},
 "price": {"job": "anchor", "eyebrow": "The Price", "headline_display": "Take It<br>Or Leave It",
           "content": {"quote": "The pre-post favourite", "price": "$3.40",
                       "said": "Anything shorter and the value has gone."}},
 "compare": {"job": "relate", "eyebrow": "The Same Mare",
             "headline_display": "The Formline That<br>Argues With Itself",
             "content": {"cols": [
                 {"tone": "yes", "k": "At the current distance",
                  "v": "Three starts, two wins and a 2nd"},
                 {"tone": "no", "k": "At the track",
                  "v": "Three starts, and not a place"}],
                 "note": "Two true things pulling opposite ways."}},
 "slate": {"job": "relate", "relates_to": "what a last-start run has to clear",
           "eyebrow": "Four Conditions", "headline_display": "What The Run<br>Has To Clear",
           "content": {"cells": [
               {"k": "Run 2nd, 3rd or 4th", "v": "Within 3.5 lengths of the winner",
                "sub": "At its latest start in the past 28 days"},
               {"k": "Shaped encouragingly for 5th to 8th",
                "v": "Less than 5 lengths from the winner",
                "sub": "When unfancied at 10 / 1 or longer"},
               {"k": "Beaten favourite", "v": "Held up for a clear run",
                "sub": "With the same rider engaged again"},
               {"k": "First-up from a spell", "v": "A trial inside the past 21 days",
                "sub": "Over a suitable distance for the run"}],
               "warn": "All four, or the horse is not a contender."}},
 "checklist": {"job": "relate", "relates_to": "the one horse worth backing",
               "eyebrow": "Before You Bet", "headline_display": "The Seven<br>Questions",
               "content": {"items": [
                   "A win strike of between 25 and 39 per cent from 10 starts or more",
                   "2 wins and 2 placings from its last 5 starts",
                   "The most recent of them within the previous 21 days",
                   "Carrying no more than 2kg above the Limit",
                   "Drawn inside barrier 8 in a field of 12 or fewer",
                   "A trainer above 15 per cent for the season",
                   "Suited by today's going and today's distance"]}},
 "steps": {"job": "orient", "eyebrow": "Barry's Frame",
           "headline_display": "Where the<br>Form Sits",
           "content": {"steps": [
               {"k": "Ability", "v": "Speed figures, pace ratings, power ratings"},
               {"k": "Form", "v": "Recent finishes, layoff patterns, workouts"},
               {"k": "Connections", "v": "Trainer, jockey and owners"},
               {"k": "Potential", "v": "Breeding, sales prices, trainer switches"},
               {"k": "Race setup", "v": "The probable pace, the draw, the styles"},
               {"k": "Conditions", "v": "The going, the rail, the distance"},
               {"k": "The price", "v": "What the market is offering against all of it"}],
               "note": "Broadly, handicapping falls into several categories."}},
 "slots": {"job": "locate", "eyebrow": "Two - Simplicity Itself",
           "headline_display": "The Pre-Post<br>Favourite",
           "content": {"tag": "Rick Hunter's little system",
                       "slots": [
                           {"k": "Consider only", "v": "The pre-post favourite"},
                           {"k": "Provided it is", "v": "Carrying top weight in a handicap"},
                           {"k": "Double your bet if", "v": "Ridden by the #1 jockey in your State"},
                           {"k": "Skip the race when", "v": "The favourite is out of the weights"}],
                       "said": "The system was simplicity itself.",
                       "chips": ["Metropolitan", "Handicaps", "Top weight", "Saturdays"]}},
 "chips": {"job": "anchor", "eyebrow": "What Goes Out", "headline_display": "Chucking Out<br>Contenders",
           "content": {"chips": [{"label": "Wrong distance", "tone": ""}, {"label": "Wrong going", "tone": ""},
                                 {"label": "Out of form", "tone": ""}, {"label": "Up in class", "tone": ""},
                                 {"label": "Badly drawn", "tone": ""}, {"label": "No trial", "tone": "last"}],
                       "foot": "Whatever survives is your race."}},
 "bars": {"job": "relate", "eyebrow": "Where The Money Goes",
          "headline_display": "Three Ways<br>To Lose",
          "content": {"bars": [
              {"label": "Backing short-priced favourites", "value": "62", "tone": "", "note": "62%"},
              {"label": "Betting every race on the card", "value": "78", "tone": "", "note": "78%"},
              {"label": "Chasing after a losing day", "value": "91", "tone": "hi", "note": "91%"}],
              "ask": "Per cent of punters who say they do it.",
              "chip": "Self-reported, one season"}},
 "ratio": {"job": "relate", "eyebrow": "The Strike Rate",
           "headline_display": "One In<br>Twelve",
           "content": {"marks": [{"tone": "win"}] + [{"tone": "loss"}] * 11,
                       "payoff": "A strike rate of one in twelve needs $13 to break even."}},
 "ladder": {"job": "relate", "eyebrow": "The Odds Ladder",
            "headline_display": "What A Price<br>Costs",
            "content": {"rows": [
                {"label": "$1.50", "value": "67"},
                {"label": "$2.00", "value": "50"},
                {"label": "$2.50", "value": "40"},
                {"label": "$3.40", "value": "29"},
                {"label": "$5.00", "value": "20"},
                {"label": "$8.00", "value": "13"},
                {"label": "$13.00", "value": "8"}],
                "footer": "Per cent needed to break even."}},
 "matrix": {"job": "relate", "eyebrow": "Placing Against Recency",
            "headline_display": "Form Points,<br>Row By Row",
            "content": {"columns": ["Under 14 days", "14-28 days", "Over 28 days"],
                        "rows": [
                            {"label": "Won last start", "cells": ["9 pts", "7 pts", "4 pts"]},
                            {"label": "Ran 2nd", "cells": ["7 pts", "5 pts", "3 pts"]},
                            {"label": "Ran 3rd", "cells": ["5 pts", "4 pts", "2 pts"]},
                            {"label": "Ran 4th", "cells": ["3 pts", "2 pts", "1 pt"]},
                            {"label": "Unplaced", "cells": ["1 pt", "1 pt", "0 pts"]}],
                        "foot": "Add the column that matches today's gap."}},
 "ledger": {"job": "relate", "eyebrow": "The Points Ledger",
            "headline_display": "Adding It<br>All Up",
            "content": {"total_label": "Total form points", "rows": [
                {"label": "Won last start", "points": "9"},
                {"label": "Winner at the distance", "points": "6"},
                {"label": "Winner at the track", "points": "5"},
                {"label": "Drawn inside six", "points": "4"},
                {"label": "Trainer over 15%", "points": "4"},
                {"label": "Down in class", "points": "3"}],
                "note": "Anything over 30 is worth a second look."}},
}
