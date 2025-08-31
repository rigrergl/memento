# Sample Use Cases for Memento

## Overview
These use cases demonstrate Memento's core capability to store, retrieve, and intelligently use long-term memories to enhance LLM interactions. Each use case includes both memory gathering and memory recall conversations.

## Use Case 1: Antonia's Family Meal Planning

### Summary
Antonia and Gordon use Memento to track family food preferences, dietary restrictions, and meal history to simplify weekly meal planning. The system remembers what works for their family of four and helps generate meal ideas that everyone will enjoy.

### Family Profile
- **Antonia**: Vegetarian
- **Gordon**: Husband, loves spicy food
- **Emma**: 8 years old, lactose intolerant
- **Jake**: 5 years old, refuses mushrooms and bell peppers

### Memory Gathering Conversations

#### Conversation 1 - Initial Setup
> **Antonia**: "I need help planning meals for my family. Let me tell you about us. I'm vegetarian but everyone else eats meat. My husband Gordon loves spicy food but the kids can't handle much heat. Emma, she's 8, is lactose intolerant. Jake is 5 and absolutely refuses to eat mushrooms or bell peppers."

> **LLM**: "I'll remember these dietary preferences for your family. To help better, what cuisines does everyone enjoy?"

> **Antonia**: "We all love Italian and Mexican food. Gordon and I enjoy Thai and Indian, but we make milder versions for the kids. Emma loves pasta in any form, and Jake is obsessed with tacos."

#### Conversation 2 - Ingredient Patterns
> **Antonia**: "We always have chicken breast, ground turkey, black beans, and lots of pasta in the pantry. I keep spinach, carrots, and onions on hand. Oh, and Gordon does the Costco runs so we always have huge amounts of rice and canned tomatoes."

### Memory Recall Conversations

#### Conversation 3 - Meal Planning
> **Gordon**: "Need to plan dinners for next week. What should we make?"

> **LLM**: "Based on your family's preferences, here's a week that works for everyone:
> - Monday: Turkey tacos (Jake loves these) with beans for Antonia
> - Tuesday: Spaghetti with meat sauce (separate vegetarian sauce for Antonia, no dairy for Emma)
> - Wednesday: Mild chicken curry with rice (Gordon enjoys spicy, make it mild for kids)
> - Thursday: Black bean quesadillas (use dairy-free cheese for Emma)
> - Friday: Build-your-own pasta bar (Emma loves pasta, everyone can customize)
> 
> All use ingredients you typically have on hand."

## Use Case 2: Liam's Learning Progress

### Summary
Liam uses Memento during study sessions to track his understanding of concepts, identify knowledge gaps, and receive personalized learning suggestions based on his demonstrated learning style and progress.

### Student Profile
- **Liam**: Calculus student
- **Learning Style**: Prefers worked examples over abstract theory
- **Current Level**: Strong in differentiation, developing integration skills

### Memory Gathering Conversations

#### Conversation 1 - Initial Assessment
> **Liam**: "I'm studying calculus. I understand derivatives pretty well - I can do power rule, product rule, and chain rule. But I'm completely lost on integration by parts."

> **LLM**: "I'll note that you're comfortable with differentiation rules but need help with integration techniques. How do you typically learn best - through examples, theory, or practice problems?"

> **Liam**: "I need to see worked examples first. Abstract theory doesn't click until I've seen it applied a few times."

#### Conversation 2 - Progress Update
> **Liam**: "Just had my quiz. Nailed the integration by parts problems! But I made stupid mistakes on the chain rule problems I thought I knew."

> **LLM**: "I'll update that you've mastered integration by parts - great progress! For chain rule, it sounds like you understand the concept but need to work on careful execution. Should we focus on attention to detail strategies?"

### Memory Recall Conversations

#### Conversation 3 - Study Session
> **Liam**: "What should I study for tomorrow's exam?"

> **LLM**: "Based on your progress:
> - **Skip:** Integration by parts (you've mastered this recently)
> - **Review quickly:** Power rule and product rule (you know these well)
> - **Focus heavily:** Chain rule problems - you understand the concept but have been making execution errors. Since you learn best through examples, let's work through 3 careful examples step-by-step
> - **New territory:** Have you covered u-substitution yet? That often appears with these other topics"

#### Conversation 4 - Adaptive Teaching
> **Liam**: "Explain how trig substitution works"

> **LLM**: "Since you learn best through worked examples rather than theory, let me show you with a concrete problem first. Consider ∫√(1-x²)dx. Watch how we substitute x = sin(θ)... [continues with step-by-step example before explaining the general principle]"

## Key Observations

### Memory Types Demonstrated
1. **Static Facts**: Dietary restrictions, family relationships
2. **Preferences**: Food preferences, learning styles
3. **Inventory/Resources**: Common ingredients, available materials
4. **Progress Tracking**: What Liam knows vs. doesn't know
5. **Historical Context**: Past struggles, recent improvements

### Memory Operations Needed
1. **Store**: Save new facts with context
2. **Retrieve**: Find relevant memories based on current conversation
3. **Update**: Modify existing facts (Liam's chain rule: understood → needs practice)
4. **Synthesize**: Combine multiple memories to generate recommendations

### Value Proposition
- **Personalization**: Responses tailored to specific individuals
- **Continuity**: Conversations build on previous interactions
- **Efficiency**: No need to re-explain context in each conversation
- **Intelligence**: Proactive suggestions based on accumulated knowledge
