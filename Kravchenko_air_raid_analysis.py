# ══════════════════════════════════════════════════════════════════════════
#   TIME SERIES ANALYSIS ПОВІТРЯНИХ ТРИВОГ В УКРАЇНІ
#   Версія 4 — фінальна, з повними поясненнями на кожному кроці
#   Джерело даних: офіційний датасет alerts.in.ua
#                  (репозиторій Vadimkin/ukrainian-air-raid-sirens-dataset)
# ══════════════════════════════════════════════════════════════════════════

def section(title, emoji="📌"):
    """Друкує гарний структурований заголовок розділу в консолі."""
    line = "═" * 70
    print(f"\n{line}")
    print(f"{emoji}  {title}")
    print(f"{line}")


def subsection(title, emoji="▸"):
    """Друкує менший підзаголовок усередині розділу."""
    print(f"\n{emoji} {title}")
    print("─" * 60)


def info(text):
    """Друкує пояснювальний текст для нефахівця."""
    print(f"   ℹ️  {text}")


def result(text):
    """Друкує підсумковий результат, виділений візуально."""
    print(f"   ✅ {text}")


def warning(text):
    """Друкує попередження, на яке варто звернути увагу."""
    print(f"   ⚠️  {text}")


# ══════════════════════════════════════════════════════════════════════════
# КРОК 0 ⚙️  ВСТАНОВЛЕННЯ ТА ІМПОРТ БІБЛІОТЕК
# ══════════════════════════════════════════════════════════════════════════
section("КРОК 0 — Підготовка середовища", "⚙️")
info("Встановлюємо та підключаємо бібліотеки для роботи з таблицями (pandas)")
info("і для побудови графіків (matplotlib). Це треба зробити один раз на старті.")

!pip install -q pandas matplotlib

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

result("Бібліотеки підключені, можна рухатись далі.")


# ══════════════════════════════════════════════════════════════════════════
# КРОК 1 📥  ЗАВАНТАЖЕННЯ ДАНИХ
# ══════════════════════════════════════════════════════════════════════════
section("КРОК 1 — Завантаження файлу з тривогами", "📥")
info("Тягнемо офіційний CSV-файл напряму з GitHub. Це готовий історичний")
info("архів тривог в Україні, зібраний на основі офіційних повідомлень.")

URL = "https://raw.githubusercontent.com/Vadimkin/ukrainian-air-raid-sirens-dataset/main/datasets/official_data_uk.csv"
df = pd.read_csv(URL)

subsection("Перевірка: чи код взагалі бачить таблицю?")
print(f"   Розмір таблиці: {df.shape[0]:,} рядків × {df.shape[1]} колонок".replace(",", " "))
print(f"   Назви колонок: {list(df.columns)}")
print("\n   Перші 5 рядків таблиці:")
display(df.head())
print("\n   Типи даних по колонках:")
print(df.dtypes)

result("Файл успішно завантажено і прочитано.")


# ══════════════════════════════════════════════════════════════════════════
# КРОК 2 🧹  ОЧИЩЕННЯ ДАНИХ ТА ПІДРАХУНОК ТРИВАЛОСТІ
# ══════════════════════════════════════════════════════════════════════════
section("КРОК 2 — Очищення даних і розрахунок тривалості", "🧹")
info("Сирі дані з інтернету майже ніколи не готові до аналізу одразу.")
info("У цьому кроці ми приводимо таблицю до чистого і коректного вигляду.")

subsection("2.1 — Перевірка назв колонок", "🔎")
COL_REGION = "oblast"
COL_START = "started_at"
COL_END = "finished_at"
info(f"Працюємо з колонками: область = '{COL_REGION}', "
     f"початок = '{COL_START}', кінець = '{COL_END}'.")

missing_cols = [c for c in [COL_REGION, COL_START, COL_END] if c not in df.columns]
if missing_cols:
    raise ValueError(
        f"Не знайдено колонки {missing_cols}. "
        f"Перевірте реальні назви колонок з Кроку 1 (df.columns) і виправте "
        f"змінні COL_REGION/COL_START/COL_END."
    )
result("Усі очікувані колонки на місці.")

subsection("2.2 — Переведення часу. Чому ми НЕ переводимо в київський час одразу", "🕐")
info("Дати в датасеті записані у форматі UTC (всесвітній час).")
info("Здавалось би, логічно одразу перевести все в київський час — але є пастка:")
info("під час переходу з літнього на зимовий час одна й та сама ГОДИНА доби")
info("(наприклад, 03:00-04:00) в Україні настає двічі поспіль.")
info("Якщо округлювати чи групувати дані саме в такий момент, Python не може")
info("однозначно зрозуміти, яку з двох однакових 03:00 мали на увазі —")
info("і падає з помилкою AmbiguousTimeError ('неоднозначний час').")
info("Тому план такий: ВСЯ математика з часом (округлення, групування)")
info("відбувається в UTC, де переходів немає і кожна хвилина унікальна.")
info("Переведення в київський час робимо ОДИН раз, у самому кінці Кроку 2,")
info("коли таблиця вже повністю готова — і тільки для показу на графіках.")

df[COL_START] = pd.to_datetime(df[COL_START], utc=True, errors="coerce")
df[COL_END] = pd.to_datetime(df[COL_END], utc=True, errors="coerce")

before = len(df)
df = df.dropna(subset=[COL_START])
after = len(df)
print(f"   Видалено рядків без коректної дати початку: {before - after}")

subsection("2.3 — Об'єднання тривог 'по областях' і 'по районах'", "🗺️")
info("Тут найважливіший і найхитріший момент усього проєкту.")
info("У датасеті є колонка 'level' — рівень деталізації запису:")
info("   • oblast  — тривога зафіксована на рівні цілої ОБЛАСТІ")
info("   • raion   — тривога зафіксована на рівні ОКРЕМОГО РАЙОНУ")
info("   • hromada — тривога зафіксована на рівні ГРОМАДИ (найдрібніше)")
info("")
info("Методика збору даних змінювалась з часом: приблизно до грудня 2025")
info("офіційні тривоги фіксувались переважно на рівні ОБЛАСТІ. А з грудня")
info("2025 року систему змінили — тривоги почали оголошувати переважно на")
info("рівні РАЙОНУ (це точніше географічно, але інакше структуровано).")
info("")
warning("Якщо просто залишити в аналізі тільки рядки рівня 'oblast', то")
warning("ВЕСЬ період з грудня 2025 і весь 2026 рік '!зникнуть' з графіків —")
warning("бо в цей період тривоги майже не фіксувались на рівні області.")
warning("Графік тренду тоді хибно показує різке падіння тривог до нуля,")
warning("хоча насправді це означає лише 'дані змінили формат', а не")
warning("'тривог стало менше'.")
info("")
info("Рішення: rядки рівня 'oblast' беремо як є. Рядки рівня 'raion'")
info("об'єднуємо назад до рівня області — групуємо їх за областю і часом")
info("початку, округленим до 10 хвилин.")
info("")
info("Чому саме 10 хвилин? Коли в одній області тривога оголошується")
info("одразу в кількох районах через спільну загрозу, повідомлення про")
info("кожен район можуть надійти не рівно одночасно, а з невеликим")
info("розривом у кілька хвилин. Округлення до 10 хвилин 'склеює' ці")
info("близькі за часом записи в одну тривогу на рівні області — так само,")
info("як одна повітряна тривога звучить одночасно для всього міста,")
info("а не оголошується по вулицях окремо. Рядки рівня 'hromada'")
info("ігноруємо — вони найдетальніші і здебільшого дублюють інформацію")
info("з oblast/raion, не додаючи нових періодів тривог.")

if "level" in df.columns:
    print("\n   Розподіл записів по рівнях (level) до обробки:")
    print(df["level"].value_counts())

    oblast_rows = df[df["level"] == "oblast"].copy()
    raion_rows = df[df["level"] == "raion"].copy()

    if len(raion_rows) > 0:
        raion_rows["start_rounded"] = raion_rows[COL_START].dt.round("10min")

        raion_grouped = (
            raion_rows
            .groupby([COL_REGION, "start_rounded"], as_index=False)
            .agg({COL_END: "max", "source": "first"})
            .rename(columns={"start_rounded": COL_START})
        )
        print(f"\n   Raion-рівень: {len(raion_rows):,} рядків по районах "
              f"згорнуто у {len(raion_grouped):,} тривог на рівні областей."
              .replace(",", " "))
    else:
        raion_grouped = raion_rows
        print("\n   Raion-рівня в даних немає.")

    common_cols = [COL_REGION, COL_START, COL_END, "source"]
    df = pd.concat(
        [oblast_rows[common_cols], raion_grouped[common_cols]],
        ignore_index=True
    )
    result(f"Після об'єднання oblast + агрегованого raion: {len(df):,} рядків."
           .replace(",", " "))
else:
    warning("Колонки 'level' немає в цьому файлі — пропускаємо цей крок.")

subsection("2.4 — Тривоги без зафіксованого завершення", "⏱️")
info("Іноді тривога вмикається, але повідомлення про її завершення з якоїсь")
info("причини не доходить до системи (технічний збій, втрата зв'язку тощо).")
info("У такому разі автор датасету застосовує просте правило: вважати, що")
info("тривога тривала 30 хвилин від початку. Ми робимо так само і додатково")
info("позначаємо такі рядки прапорцем 'naive' = True, щоб завжди було видно,")
info("де тривалість РЕАЛЬНА, а де ДОДУМАНА.")

if "naive" in df.columns:
    info("Колонка 'naive' вже є в датасеті — використовуємо її як є.")
else:
    info("Колонки 'naive' немає в цьому файлі. Створюємо її вручну.")
    df["naive"] = df[COL_END].isna()

missing_end_mask = df[COL_END].isna()
n_missing_end = missing_end_mask.sum()
print(f"   Тривог без зафіксованого часу завершення: {n_missing_end:,}".replace(",", " "))

df.loc[missing_end_mask, COL_END] = df.loc[missing_end_mask, COL_START] + pd.Timedelta(minutes=30)

subsection("2.5 — Розрахунок тривалості кожної тривоги", "📏")
df["duration_minutes"] = (df[COL_END] - df[COL_START]).dt.total_seconds() / 60
info("Тривалість = час завершення мінус час початку, у хвилинах.")

subsection("2.6 — Видалення аномалій", "🧽")
info("Технічні збої іноді дають абсурдні значення: від'ємну тривалість або")
info("тривогу, що 'триває' кілька днів поспіль. Прибираємо такі викиди.")
before = len(df)
df = df[(df["duration_minutes"] > 0) & (df["duration_minutes"] < 24 * 60)]
after = len(df)
print(f"   Видалено рядків з аномальною тривалістю (≤0 або >24 год): {before - after}")

subsection("2.7 — Переведення у київський час (вже фінальний крок)", "🇺🇦")
info("Таблиця повністю очищена і об'єднана — тепер, і тільки тепер, безпечно")
info("перевести час у місцевий київський, щоб графіки 'за годиною доби' і")
info("'за днем тижня' показували реальний український час, а не UTC.")
df[COL_START] = df[COL_START].dt.tz_convert("Europe/Kyiv")
df[COL_END] = df[COL_END].dt.tz_convert("Europe/Kyiv")

df["hour"] = df[COL_START].dt.hour
df["weekday"] = df[COL_START].dt.day_name()
df["weekday_num"] = df[COL_START].dt.weekday
df["year_month"] = df[COL_START].dt.to_period("M")

subsection("Підсумкова таблиця після очищення", "📋")
print(f"   Рядків залишилось: {len(df):,}".replace(",", " "))
display(df[[COL_REGION, COL_START, COL_END, "duration_minutes", "naive"]].head())


# ══════════════════════════════════════════════════════════════════════════
# КРОК 2.9 🔍  SANITY-CHECKS — ПЕРЕВІРКА ДАНИХ "НА ЗДОРОВИЙ ГЛУЗД"
# ══════════════════════════════════════════════════════════════════════════
section("КРОК 2.9 — Sanity-checks: чи виглядають дані правдоподібно?", "🔍")
info("Це не доказ на 100%, що дані ідеальні, а швидкі автоматичні перевірки,")
info("які одразу сигналізують, якщо щось явно не так. Переглядайте їх кожного")
info("разу, коли запускаєте код наново — особливо після оновлення датасету.")

subsection("Перевірка 1 — кількість областей", "1️⃣")
n_regions = df[COL_REGION].nunique()
print(f"   Унікальних областей у даних: {n_regions}")
info("В Україні 24 області + АР Крим + м. Київ окремо ≈ 25-27 унікальних назв.")
if n_regions < 20 or n_regions > 30:
    warning("Число суттєво відрізняється від очікуваного. Можливо, є дублікати")
    warning("назв (наприклад 'Київська область' і 'Київська обл.' як різні рядки).")
else:
    result("Кількість областей виглядає адекватно.")

print("\n   Повний список областей і кількість тривог:")
print(df[COL_REGION].value_counts())

subsection("Перевірка 2 — список назв (візуальна перевірка дублікатів)", "2️⃣")
unique_names_sorted = sorted(df[COL_REGION].unique())
info("Перегляньте список нижче — чи нема схожих назв, які мали б бути однією:")
for name in unique_names_sorted:
    print(f"      • {name}")

subsection("Перевірка 3 — медіанна тривалість і частка 'добудованих' тривог", "3️⃣")
median_duration = df["duration_minutes"].median()
naive_share = df["naive"].mean() * 100 if "naive" in df.columns else None
print(f"   Медіанна тривалість тривоги: {median_duration:.1f} хв")
if naive_share is not None:
    print(f"   Частка тривог із добудованим (+30 хв) часом завершення: {naive_share:.1f}%")
    if naive_share > 30:
        warning("Понад 30% тривог мають добудований час завершення — статистика")
        warning("тривалості може бути зміщена в бік рівно 30 хвилин.")
    else:
        result("Частка добудованих тривог у прийнятних межах.")

subsection("Перевірка 4 — пік активності по днях", "4️⃣")
alerts_per_day = df.groupby(df[COL_START].dt.date).size()
print(f"   Середня кількість тривог на день (по всій країні): {alerts_per_day.mean():.1f}")
print(f"   Максимум за один день: {alerts_per_day.max()} ({alerts_per_day.idxmax()})")
print(f"   Мінімум за один день: {alerts_per_day.min()} ({alerts_per_day.idxmin()})")
info("Перевірте вручну: чи день із максимумом — це реально відома масована атака?")


# ══════════════════════════════════════════════════════════════════════════
# КРОК 3 📊  ГРАФІКИ ТА СТАТИСТИКА
# ══════════════════════════════════════════════════════════════════════════
section("КРОК 3 — Графіки та описова статистика", "📊")

subsection("3.1 — Пікові години доби", "🕐")
info("Показує, о котрій годині доби тривоги оголошуються найчастіше.")
hourly_counts = df["hour"].value_counts().sort_index()

plt.figure(figsize=(10, 5))
plt.bar(hourly_counts.index, hourly_counts.values, color="#d62728")
plt.title("Кількість тривог за годинами доби (київський час)")
plt.xlabel("Година доби")
plt.ylabel("Кількість тривог")
plt.xticks(range(0, 24))
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.show()

peak_hour = hourly_counts.idxmax()
result(f"Пікова година доби: {peak_hour}:00 ({hourly_counts.max():,} тривог)".replace(",", " "))

subsection("3.2 — Тривоги за днями тижня", "📅")
info("Показує, чи є дні тижня, в які тривоги трапляються частіше за інші.")
weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
weekday_order_uk = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]
weekday_counts = df["weekday"].value_counts().reindex(weekday_order)

plt.figure(figsize=(10, 5))
plt.bar(weekday_order_uk, weekday_counts.values, color="#1f77b4")
plt.title("Кількість тривог за днями тижня")
plt.xlabel("День тижня")
plt.ylabel("Кількість тривог")
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.show()

peak_weekday_idx = weekday_counts.values.argmax()
result(f"Найактивніший день тижня: {weekday_order_uk[peak_weekday_idx]} "
       f"({weekday_counts.values[peak_weekday_idx]:,} тривог)".replace(",", " "))

subsection("3.3 — Топ-10 найактивніших областей", "🗺️")
info("Показує, які області найчастіше потрапляли під тривоги за весь період.")
region_counts = df[COL_REGION].value_counts().head(10)

plt.figure(figsize=(10, 6))
plt.barh(region_counts.index[::-1], region_counts.values[::-1], color="#2ca02c")
plt.title("Топ-10 областей за кількістю тривог")
plt.xlabel("Кількість тривог")
plt.tight_layout()
plt.show()

print("\n   Топ-3 найактивніших області:")
for i, (region, count) in enumerate(region_counts.head(3).items(), 1):
    print(f"      {i}. {region}: {count:,} тривог".replace(",", " "))

subsection("3.4 — Місяць з найбільшою сумарною тривалістю тривог", "📈")
info("Показує не кількість тривог, а сумарний 'час під тривогою' за місяць —")
info("місяць може мати мало тривог, але дуже довгих, і навпаки.")
monthly_duration = df.groupby("year_month")["duration_minutes"].sum().sort_values(ascending=False)
monthly_duration_sorted_by_time = df.groupby("year_month")["duration_minutes"].sum().sort_index()

plt.figure(figsize=(14, 5))
plt.plot(monthly_duration_sorted_by_time.index.astype(str), monthly_duration_sorted_by_time.values, marker="o", color="#9467bd")
plt.title("Сумарна тривалість тривог по місяцях (хвилини)")
plt.xlabel("Місяць")
plt.ylabel("Сумарна тривалість, хв")
plt.xticks(rotation=90)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

top_month = monthly_duration.index[0]
top_month_minutes = monthly_duration.iloc[0]
top_month_hours = top_month_minutes / 60
result(f"Місяць з найбільшою сумарною тривалістю тривог: {top_month}")
result(f"Сумарна тривалість: {top_month_minutes:,.0f} хв (~{top_month_hours:.1f} год)".replace(",", " "))


# ══════════════════════════════════════════════════════════════════════════
# КРОК 3.5 🔄  ПЕРЕХРЕСНА ЗВІРКА З ВОЛОНТЕРСЬКИМ ДАТАСЕТОМ
# ══════════════════════════════════════════════════════════════════════════
section("КРОК 3.5 — Перехресна звірка з незалежним джерелом даних", "🔄")
info("Офіційний і волонтерський датасети збираються повністю незалежно один")
info("від одного. Якщо обидва показують схожий рейтинг 'найактивніших")
info("областей' — це сильний доказ, що наша методика обробки даних коректна.")
info("Якщо рейтинги розходяться — це сигнал перевірити код глибше.")

VOLUNTEER_URL = "https://raw.githubusercontent.com/Vadimkin/ukrainian-air-raid-sirens-dataset/main/datasets/volunteer_data_uk.csv"

try:
    df_vol = pd.read_csv(VOLUNTEER_URL)
    print(f"   Колонки волонтерського датасету: {list(df_vol.columns)}")

    vol_region_candidates = [c for c in df_vol.columns if c.lower() in
                              ("region", "oblast", "regionname", "region_name")]
    vol_start_candidates = [c for c in df_vol.columns if "start" in c.lower()]

    if vol_region_candidates and vol_start_candidates:
        VOL_REGION = vol_region_candidates[0]
        VOL_START = vol_start_candidates[0]
        info(f"Використовуємо колонки: регіон='{VOL_REGION}', старт='{VOL_START}'")

        vol_top = df_vol[VOL_REGION].value_counts().head(5)
        official_top = df[COL_REGION].value_counts().head(5)

        print("\n   Топ-5 областей за офіційними даними (наша оброблена таблиця):")
        print(official_top)
        print("\n   Топ-5 областей за волонтерськими даними (незалежне джерело):")
        print(vol_top)

        official_top3_names = set(official_top.head(3).index)
        vol_top3_names = set(vol_top.head(3).index)
        overlap = official_top3_names & vol_top3_names

        print(f"\n   Співпадіння в топ-3 між двома джерелами: {len(overlap)} з 3 областей.")
        if len(overlap) >= 2:
            result("Хороший знак — обидва незалежні джерела узгоджуються по топ-областях.")
        else:
            warning("Топ-3 області суттєво розходяться між джерелами. Варто перевірити")
            warning("назви областей вручну (можливі розбіжності в написанні).")
    else:
        warning("Не вдалося автоматично визначити колонки регіону/часу у волонтерському")
        warning("датасеті. Перегляньте df_vol.head() вручну для звірки.")
        display(df_vol.head())

except Exception as e:
    warning(f"Не вдалося завантажити волонтерський датасет для звірки: {e}")
    info("Цей крок не критичний для решти аналізу — можна пропустити.")


# ══════════════════════════════════════════════════════════════════════════
# КРОК 4 🔮  ПРОСТЕ ПРОГНОЗУВАННЯ НА ОСНОВІ КОВЗНОГО СЕРЕДНЬОГО
# ══════════════════════════════════════════════════════════════════════════
section("КРОК 4 — Простий прогноз тренду (baseline-модель)", "🔮")
info("Це найпростіший можливий вид прогнозування — 'наївний прогноз':")
info("припускаємо, що завтра буде приблизно стільки ж тривог, скільки в")
info("середньому було за останні 30 днів. Це не повноцінна модель (на кшталт")
info("ARIMA чи Prophet), а демонстраційний базовий рівень для порівняння.")

daily_counts = df.groupby(df[COL_START].dt.date).size()
daily_counts.index = pd.to_datetime(daily_counts.index)
daily_counts = daily_counts.sort_index()

full_date_range = pd.date_range(daily_counts.index.min(), daily_counts.index.max(), freq="D")
daily_counts = daily_counts.reindex(full_date_range, fill_value=0)

WINDOW_SHORT = 7
WINDOW_LONG = 30
rolling_short = daily_counts.rolling(window=WINDOW_SHORT).mean()
rolling_long = daily_counts.rolling(window=WINDOW_LONG).mean()

last_30_avg = daily_counts.tail(WINDOW_LONG).mean()
forecast_dates = pd.date_range(daily_counts.index[-1] + pd.Timedelta(days=1), periods=7, freq="D")
forecast_values = [last_30_avg] * 7

plt.figure(figsize=(14, 6))
plt.plot(daily_counts.index, daily_counts.values, alpha=0.3, label="Фактична кількість тривог/день", color="gray")
plt.plot(rolling_short.index, rolling_short.values, label=f"Ковзне середнє ({WINDOW_SHORT} днів)", color="#1f77b4")
plt.plot(rolling_long.index, rolling_long.values, label=f"Ковзне середнє ({WINDOW_LONG} днів)", color="#d62728")
plt.plot(forecast_dates, forecast_values, "--", label="Прогноз на наступні 7 днів", color="#2ca02c", linewidth=2)
plt.title("Тренд кількості тривог та простий прогноз на основі середнього")
plt.xlabel("Дата")
plt.ylabel("Кількість тривог за день")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

result(f"Простий прогноз: у середньому очікується ~{last_30_avg:.1f} тривог/день")
info("(розраховано як середнє значення за останні 30 днів наявних даних)")


# ══════════════════════════════════════════════════════════════════════════
# КРОК 5 🌆  ПРОГНОЗ 1 — ВІЛЬНИЙ ЧАС У ДНІПРІ В ЛИПНІ (06:00-23:00)
# ══════════════════════════════════════════════════════════════════════════
section("КРОК 5 — Прогноз: вільні хвилини в Дніпрі, липень, 06:00-23:00", "🌆")
info("Метод: емпірична (історична) ймовірність. Беремо ВСІ тривоги в")
info("Дніпропетровській області за всі наявні липні, накладаємо їх на вікно")
info("доби 06:00-23:00 і рахуємо, скільки хвилин цього вікна в середньому")
info("займала тривога за один день. Решта вікна — час без тривоги.")
warning("Датасет дає дані на рівні ОБЛАСТІ, не міста. Тому 'тривога в Дніпрі'")
warning("тут технічно означає 'тривога в Дніпропетровській області' —")
warning("точнішої гранулярності офіційні дані не дають. Це варто чітко")
warning("проговорити, захищаючи проєкт.")

DNIPRO_REGION_NAME_CANDIDATES = [r for r in df[COL_REGION].unique() if "Дніпропетровськ" in r]
if not DNIPRO_REGION_NAME_CANDIDATES:
    warning("Не знайдено область з назвою, що містить 'Дніпропетровськ'.")
    print(f"   Наявні унікальні назви областей: {sorted(df[COL_REGION].unique())}")
else:
    DNIPRO_REGION = DNIPRO_REGION_NAME_CANDIDATES[0]
    info(f"Використовуємо назву області з датасету: '{DNIPRO_REGION}'")

    df_dnipro_july = df[
        (df[COL_REGION] == DNIPRO_REGION) &
        (df[COL_START].dt.month == 7)
    ].copy()

    print(f"   Знайдено тривог у Дніпропетровській області за всі липні: {len(df_dnipro_july):,}".replace(",", " "))

    if len(df_dnipro_july) == 0:
        warning("Немає даних по липню для цієї області — прогноз неможливий.")
    else:
        years_present = sorted(df_dnipro_july[COL_START].dt.year.unique())
        print(f"   Дані охоплюють липні таких років: {years_present}")

        WINDOW_START_HOUR = 6
        WINDOW_END_HOUR = 23
        window_minutes_total = (WINDOW_END_HOUR - WINDOW_START_HOUR) * 60

        def overlap_minutes_with_window(row, window_start_h, window_end_h):
            """Скільки хвилин ця тривога перетинається з вікном 06:00-23:00 свого дня."""
            day = row[COL_START].normalize()
            window_start = day + pd.Timedelta(hours=window_start_h)
            window_end = day + pd.Timedelta(hours=window_end_h)
            overlap_start = max(row[COL_START], window_start)
            overlap_end = min(row[COL_END], window_end)
            overlap = (overlap_end - overlap_start).total_seconds() / 60
            return max(overlap, 0)

        df_dnipro_july["overlap_min"] = df_dnipro_july.apply(
            overlap_minutes_with_window, axis=1,
            window_start_h=WINDOW_START_HOUR, window_end_h=WINDOW_END_HOUR
        )

        alert_minutes_per_day = df_dnipro_july.groupby(df_dnipro_july[COL_START].dt.date)["overlap_min"].sum()

        all_july_dates = pd.Series(pd.date_range(
            start=f"{min(years_present)}-07-01", end=f"{max(years_present)}-07-31", freq="D"
        ))
        all_july_dates = all_july_dates[all_july_dates.dt.month == 7]
        data_min_date = df[COL_START].min().tz_localize(None).normalize()
        data_max_date = df[COL_START].max().tz_localize(None).normalize()
        all_july_dates = all_july_dates[(all_july_dates >= data_min_date) & (all_july_dates <= data_max_date)]

        alert_minutes_per_day_full = alert_minutes_per_day.reindex(
            [d.date() for d in all_july_dates], fill_value=0
        )

        avg_alert_minutes = alert_minutes_per_day_full.mean()
        avg_free_minutes = window_minutes_total - avg_alert_minutes

        print(f"\n   Усього липневих днів у даних: {len(alert_minutes_per_day_full)}")
        print(f"   Середньо ПІД ТРИВОГОЮ у вікні 06:00-23:00: {avg_alert_minutes:.1f} хв")
        print(f"   Середньо БЕЗ ТРИВОГИ у вікні 06:00-23:00: {avg_free_minutes:.1f} хв "
              f"(з {window_minutes_total} можливих)")

        result(f"У випадковий липневий день у Дніпрі (Дніпропетровській області) "
               f"очікується ~{avg_free_minutes:.0f} хв БЕЗ тривоги протягом 06:00-23:00.")
        info(f"Оцінка базується на {len(years_present)} липні(ях) наявних даних ({years_present}).")
        warning("Чим менше років даних, тим менш надійна ця оцінка.")


# ══════════════════════════════════════════════════════════════════════════
# КРОК 6 🎯  ПРОГНОЗ 2 — ЙМОВІРНІСТЬ ТРИВОГИ В КИЄВІ, 6 СЕРПНЯ 2026, 13:00
# ══════════════════════════════════════════════════════════════════════════
section("КРОК 6 — Прогноз: ймовірність тривоги в Києві о 13:00, 6 серпня 2026", "🎯")
info("Та сама ідея емпіричної ймовірності, але звужена саме до СЕРПНЯ —")
info("частота тривог має сезонність, тому серпень минулих років є найбільш")
info("релевантним орієнтиром для прогнозу на серпень 2026.")
info("Формула: ймовірність = (днів, коли о 13:00 тривала тривога) / (усіх")
info("серпневих днів у даних) × 100%.")

KYIV_REGION_NAME_CANDIDATES = [r for r in df[COL_REGION].unique() if "Київ" in r]
print(f"   Знайдені варіанти назв, що містять 'Київ': {KYIV_REGION_NAME_CANDIDATES}")

if not KYIV_REGION_NAME_CANDIDATES:
    warning("Не знайдено область з назвою, що містить 'Київ'.")
else:
    kyiv_city_candidates = [r for r in KYIV_REGION_NAME_CANDIDATES if "область" not in r.lower() and "обл" not in r.lower()]
    KYIV_REGION = kyiv_city_candidates[0] if kyiv_city_candidates else KYIV_REGION_NAME_CANDIDATES[0]
    info(f"Використовуємо назву з датасету: '{KYIV_REGION}'")

    df_kyiv_august = df[
        (df[COL_REGION] == KYIV_REGION) &
        (df[COL_START].dt.month == 8)
    ].copy()

    years_present_aug = sorted(df_kyiv_august[COL_START].dt.year.unique()) if len(df_kyiv_august) else []
    print(f"   Серпневих тривог у Києві знайдено: {len(df_kyiv_august):,} (роки: {years_present_aug})".replace(",", " "))

    if len(df_kyiv_august) == 0:
        warning("Немає даних по серпню для Києва — прогноз неможливий цим методом.")
    else:
        data_min_date = df[COL_START].min().tz_localize(None).normalize()
        data_max_date = df[COL_START].max().tz_localize(None).normalize()

        all_august_dates = pd.Series(pd.date_range(
            start=f"{min(years_present_aug)}-08-01", end=f"{max(years_present_aug)}-08-31", freq="D"
        ))
        all_august_dates = all_august_dates[all_august_dates.dt.month == 8]
        all_august_dates = all_august_dates[(all_august_dates >= data_min_date) & (all_august_dates <= data_max_date)]

        TARGET_HOUR = 13

        def alert_active_at_hour(day_date, hour, alerts_df):
            """Перевіряє, чи є хоч одна тривога, що триває в момент day_date+hour:00."""
            moment = pd.Timestamp(day_date) + pd.Timedelta(hours=hour)
            moment = moment.tz_localize("Europe/Kyiv", ambiguous=True, nonexistent="shift_forward")
            mask = (alerts_df[COL_START] <= moment) & (alerts_df[COL_END] > moment)
            return mask.any()

        results = [alert_active_at_hour(d.date(), TARGET_HOUR, df_kyiv_august) for d in all_august_dates]

        n_days_total = len(results)
        n_days_with_alert = sum(results)
        probability = (n_days_with_alert / n_days_total * 100) if n_days_total > 0 else None

        print(f"\n   Усього серпневих днів у даних: {n_days_total}")
        print(f"   З них днів, коли о 13:00 тривала тривога: {n_days_with_alert}")

        if probability is not None:
            result(f"Ймовірність, що 6 серпня 2026 о 13:00 у Києві буде тривога: ~{probability:.1f}%")
            info(f"Оцінка базується на серпнях {years_present_aug} — лише {n_days_total} спостережень.")
            warning("Довірчий інтервал такої оцінки доволі широкий — це варто чітко")
            warning("проговорити, захищаючи проєкт.")
        else:
            warning("Недостатньо даних для розрахунку ймовірності.")


# ══════════════════════════════════════════════════════════════════════════
section("ГОТОВО — аналіз завершено", "🏁")
print("   Усі кроки виконано успішно. Прокрутіть вище, щоб переглянути всі")
print("   графіки, перевірки та прогнози.")
print("═" * 70)
