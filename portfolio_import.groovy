// Script PortfolioPerformance - importa da GitHub Raw
import java.net.URL
import groovy.json.JsonSlurper
import java.text.SimpleDateFormat

def githubRawUrl = "https://raw.githubusercontent.com/TUO_USERNAME/scrape-fonte-dinamico/main/fonte_dinamico.json"
println "🌐 Scaricando NAV da GitHub: $githubRawUrl"

try {
    def url = new URL(githubRawUrl)
    def jsonText = url.text
    def data = new JsonSlurper().parseText(jsonText)
    
    println "📊 Trovati ${data.nav_history.size()} punti NAV"
    
    data.nav_history.each { entry ->
        def date = new SimpleDateFormat("yyyy-MM-dd").parse(entry.date)
        def price = entry.nav as BigDecimal
        
        // Crea prezzo (sostituisci "FONTE DINAMICO" con ticker nel tuo portafoglio)
        createOrUpdatePrice("FONTE DINAMICO", date, price, "EUR")
        println "➕ ${entry.date}: €${price}"
    }
    
    println "✅ Import completato!"
} catch (Exception e) {
    println "❌ Errore: ${e.message}"
}
