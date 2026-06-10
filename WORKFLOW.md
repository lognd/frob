Here's the path I want your development to go through:

1. Read the README.md and start thinking through the design and write stuff in `docs/`. Start high-level and think REALLY HARD about any architectural issues and solve architectural problems before even implementing (i.e. how is error handling going to work in a pipeline?)
2. As you write the docs, make a `TODO.md` that you can keep a hierarchical list of everything that must be done.
3. Write the outlines/stubs for each thing you think you will need. Try to follow your hierarchical list.
4. Dispatch test generation from pulling from design docs (maybe format design docs in a very parsable manner? auto parsing?) and stubs and give to Haikus (unit first, then integration to see how units interact, and then system tests that test the system from start-to-finish).
5. Make sure that the workflow is intuitive and if there's any "uh oh" moments where you made a bad decision, pause and do a redesign (this applies to any step, but the later you go, the harder it is obviously).
6. Dispatch the implementation to Haikus, focus on readability, then validation (if python, think Pydantic) and robustness, then efficiency.
7. Run the tools and fix all the errors. Try and stay with local, but if it can't be fixed SUPER easily, then you can pull from everything normally.
8. Write documentation (docstrings and docs/)
