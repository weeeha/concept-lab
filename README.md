# Concept Lab

A tool for the vibefolio: give it a project idea, get back a concept piece that looks like the
thing exists. A written brief, a GitHub repo with realistic (untested) code, a 3D model of the
hardware, photos of it "in the wild", a short video, and a case-study page on vyhouski.com.

Every piece is labeled **Concept**. These illustrate ideas and direction, not shipped work.

## Use

In Claude Code, with this repo's plugin installed:

```
/concept-lab:concept <dump the idea here, voice-to-text is fine>
```

The pipeline stops once, after the brief, so the idea is agreed before anything costs money.
Then it runs the rest without asking.

## Install the plugin

```bash
claude plugin marketplace add "$HOME/ClaudeCode Projects/Concept Lab"
```

```bash
claude plugin install concept-lab@concept-lab-marketplace
```

Restart Claude Code after installing or updating.

## Concepts

| Slug | Idea | Status |
|---|---|---|
| `robot-planter` | A plant pot on wheels that walks at night and finds the sun | Live: https://vyhouski.com/projects/robot-planter |
