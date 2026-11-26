package io.github.stringmanolo.KyaniteAndroid

import android.content.Context
import android.content.res.Configuration
import android.content.res.Resources
import java.util.Locale

/**
 * UI language. English is the default; Spanish, Russian and Simplified Chinese are translated from
 * res/raw/i18n_*.tsv (English text <TAB> translation). A text with no entry simply stays in English.
 *
 * Which language is used:
 *  - if the user ever picked one in Settings > Appearance, that choice is kept forever ("ui_lang");
 *  - otherwise the system language is used when it is one of ours, and English when it is not.
 * Nothing is saved until the user chooses, so the automatic detection can never override a decision
 * (for example: system in Russian, user picks Spanish -> the app stays in Spanish after a restart).
 */
object L {
    val CODES = listOf("en", "es", "ru", "zh-CN")
    val NAMES = listOf("English", "Español", "Русский", "中文（简体）")

    private val table = HashMap<String, String>()
    @Volatile private var loadedFor = ""

    /** The language the user picked, or "" if they never did. */
    fun chosen(): String {
        val c = prefs.getString("ui_lang", "") ?: ""
        return if (c in CODES) c else ""
    }

    /** The language in use right now. */
    fun current(): String = chosen().ifEmpty { detect() }

    /** First language of the system's list that we translate (English if the first one is English or none matches). */
    fun detect(): String {
        val list = Resources.getSystem().configuration.locales
        for (i in 0 until list.size()) {
            when (list.get(i).language) {
                "en" -> return "en"
                "es" -> return "es"
                "ru" -> return "ru"
                "zh" -> return "zh-CN"
            }
        }
        return "en"
    }

    /** Saves the user's decision. This is the only place that writes it. */
    fun choose(code: String) {
        if (code !in CODES) return
        prefs.edit().putString("ui_lang", code).apply()
    }

    private fun resFor(code: String): Int = when (code) {
        "es" -> R.raw.i18n_es
        "ru" -> R.raw.i18n_ru
        "zh-CN" -> R.raw.i18n_zh_cn
        else -> 0
    }

    private fun ensure(code: String) {
        if (loadedFor == code) return
        synchronized(table) {
            if (loadedFor == code) return
            table.clear()
            val res = resFor(code)
            if (res != 0) {
                try {
                    App.instance.resources.openRawResource(res).bufferedReader(Charsets.UTF_8).useLines { lines ->
                        for (line in lines) {
                            if (line.isEmpty() || line[0] == '#') continue
                            val tab = line.indexOf('\t')
                            if (tab <= 0) continue
                            table[unescape(line.substring(0, tab))] = unescape(line.substring(tab + 1))
                        }
                    }
                } catch (_: Exception) {
                    table.clear()
                }
            }
            loadedFor = code
        }
    }

    private fun unescape(s: String): String {
        if (s.indexOf('\\') < 0) return s
        val sb = StringBuilder(s.length)
        var i = 0
        while (i < s.length) {
            val c = s[i]
            if (c == '\\' && i + 1 < s.length) {
                when (s[i + 1]) {
                    'n' -> sb.append('\n')
                    't' -> sb.append('\t')
                    '\\' -> sb.append('\\')
                    else -> sb.append(c).append(s[i + 1])
                }
                i += 2
            } else {
                sb.append(c)
                i++
            }
        }
        return sb.toString()
    }

    /** Translates a fixed UI text. Unknown texts (and English) are returned unchanged. */
    fun t(s: String): String {
        val code = current()
        if (code == "en") return s
        ensure(code)
        return table[s] ?: s
    }

    /** Translates a format string (use %s / %d) and fills it in. */
    fun f(fmt: String, vararg args: Any?): String = String.format(Locale.ROOT, t(fmt), *args)

    /** A context whose resources use the app language (system dialogs such as the date picker follow it). */
    fun wrap(base: Context): Context {
        val loc = when (current()) {
            "es" -> Locale("es")
            "ru" -> Locale("ru")
            "zh-CN" -> Locale.SIMPLIFIED_CHINESE
            else -> Locale.ENGLISH
        }
        val cfg = Configuration(base.resources.configuration)
        cfg.setLocale(loc)
        return base.createConfigurationContext(cfg)
    }
}
