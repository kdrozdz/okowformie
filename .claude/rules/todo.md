# To-do — nic nie ucieka z kontekstu czatu

Ten plik nie ma `paths:` — obowiązuje w każdej sesji, niezależnie od tego,
nad jakimi plikami akurat trwa praca.

Kiedy podczas pracy (review, debugowanie, eksploracja, `/code-review`,
`qa-agent`) natrafisz na coś, co jest realnym problemem, luką lub
niespójnością, ale **nie wchodzi w zakres bieżącego taska** (inny plik,
inna domenowa aplikacja, inna faza, świadomie odłożona decyzja) —
**zawsze dopisz to do `docs/todo/TODO.md`**, zanim skończysz turę. Samo
wspomnienie w odpowiedzi na czacie nie wystarcza — rozmowa znika z
kontekstu, plik zostaje.

Format wpisu i statusy: `docs/todo/README.md`. Zawsze dołącz link/ścieżkę
do kontekstu (plik:linia, plan taska w `docs/tasks/`, commit), żeby dało
się to podjąć później bez odtwarzania śledztwa od zera.

Nie usuwaj wpisów po zamknięciu — oznacz `[zrobione]` z linkiem do
commita/PR i zostaw jako historię, tak jak w `docs/decisions/` i
`docs/tasks/`.
