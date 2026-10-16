\# Reflection (Lab 5)



1\. Which issues were easiest and hardest to fix?

Flake8 style issues and Pylint naming and docstring issues were easiest, because the tool says exactly what to change. The hardest were the security issues, such as unsafe tar extraction and the unverified SSL context, because I had to understand the attack first. Bandit kept reporting B310 until I replaced urlopen with HTTPSConnection.



2\. Did the tools give false positives or miss real problems?

The hardcoded password and random warnings (B105, B311) can be judgement calls, but here both were real problems. More importantly, the tools missed real bugs: smoker "no" being treated as a smoker, a negative premium, the age ignoring the birthday, instalments rounded down, and the 29 Feb crash. I found these only by running the program and reading the output.



3\. How would you integrate static analysis into your workflow?

Run Flake8 and Pylint before every commit (a pre-commit hook) and Bandit plus tests in CI, such as GitHub Actions, so a bad score blocks the merge.



4\. What did static analysis contribute to code quality?

Pylint went from 5.73 to 10, Bandit from 10 issues to 0, and Flake8 from 19 to 0. The code is cleaner, safer and easier to review. But static analysis does not replace testing, because it finds patterns, not wrong business logic.

