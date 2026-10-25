import AppIntents
import Foundation
import WidgetKit

private enum MyraShortcutError: LocalizedError {
    case connectionMissing
    case tokenMissing
    case insecureEndpoint
    case invalidObjective
    case rejected(Int)

    var errorDescription: String? {
        switch self {
        case .connectionMissing:
            return "Configure a conexão da MYRA no app antes de usar a Siri."
        case .tokenMissing:
            return "O token remoto da MYRA não está salvo no Keychain."
        case .insecureEndpoint:
            return "O endpoint remoto precisa usar HTTPS e terminar em /remote/v1."
        case .invalidObjective:
            return "A tarefa deve ter entre 1 e 1.200 caracteres."
        case let .rejected(code):
            return "A API da MYRA recusou a solicitação (HTTP \(code))."
        }
    }
}

private enum MyraShortcutClient {
    static func request(path: String, method: String, body: Data? = nil) async throws -> (Data, Int) {
        guard let rawBaseURL = UserDefaults.standard.string(forKey: "myra.remote.baseURL") else {
            throw MyraShortcutError.connectionMissing
        }
        let baseURL = rawBaseURL.trimmingCharacters(in: .whitespacesAndNewlines)
            .trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard let components = URLComponents(string: baseURL),
              let scheme = components.scheme?.lowercased(),
              let host = components.host,
              !host.isEmpty,
              components.user == nil,
              components.password == nil,
              components.query == nil,
              components.fragment == nil,
              components.path == "/remote/v1" else {
            throw MyraShortcutError.insecureEndpoint
        }
        let isLoopback = ["localhost", "127.0.0.1", "::1"].contains(host.lowercased())
        guard scheme == "https" || (scheme == "http" && isLoopback) else {
            throw MyraShortcutError.insecureEndpoint
        }
        guard let token = KeychainTokenStore.load(), !token.isEmpty else {
            throw MyraShortcutError.tokenMissing
        }
        guard let url = URL(string: baseURL + "/" + path) else {
            throw MyraShortcutError.connectionMissing
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 30
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = body
        }
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw MyraShortcutError.rejected(-1)
        }
        return (data, http.statusCode)
    }
}

struct StartMyraTaskIntent: AppIntent {
    static var title: LocalizedStringResource = "Executar tarefa na MYRA"
    static var description = IntentDescription("Envia uma tarefa para o computador que executa a MYRA.")
    static var openAppWhenRun = false

    @Parameter(title: "Tarefa", description: "O que a MYRA deve fazer no computador?")
    var objective: String

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let cleaned = objective.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleaned.isEmpty, cleaned.count <= 1200 else {
            throw MyraShortcutError.invalidObjective
        }
        let body = try JSONSerialization.data(withJSONObject: ["objetivo": cleaned, "max_passos": 30])
        let (_, status) = try await MyraShortcutClient.request(path: "task", method: "POST", body: body)
        guard (200..<300).contains(status) else { throw MyraShortcutError.rejected(status) }
        return .result(dialog: "Tarefa enviada para a MYRA. Acompanhe o progresso abrindo o app MYRA.")
    }
}

struct GetMyraStatusIntent: AppIntent {
    static var title: LocalizedStringResource = "Consultar estado da MYRA"
    static var description = IntentDescription("Consulta o estado da tarefa atual no computador da MYRA.")
    static var openAppWhenRun = false

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let (data, status) = try await MyraShortcutClient.request(path: "status", method: "GET")
        guard (200..<300).contains(status) else { throw MyraShortcutError.rejected(status) }
        let current = try JSONDecoder().decode(RemoteTaskStatus.self, from: data)
        if let shared = UserDefaults(suiteName: "group.com.myra.mobile") {
            shared.set(current.state, forKey: "myra.widget.state")
            shared.set(current.stepNumber, forKey: "myra.widget.stepNumber")
            shared.set(current.totalSteps, forKey: "myra.widget.totalSteps")
            shared.set(Date().timeIntervalSince1970, forKey: "myra.widget.updatedAt")
            WidgetCenter.shared.reloadTimelines(ofKind: "MyraWidget")
        }
        var message = "Estado da MYRA: \(current.state)."
        if let objective = current.objective, !objective.isEmpty {
            message += " Tarefa: \(objective)."
        }
        if current.totalSteps > 0 {
            message += " Passo \(current.stepNumber) de \(current.totalSteps)."
        }
        if let error = current.error, !error.isEmpty {
            message += " Erro: \(error)."
        }
        return .result(dialog: "\(message)")
    }
}

struct MyraAppShortcuts: AppShortcutsProvider {
    @AppShortcutsBuilder
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: StartMyraTaskIntent(),
            phrases: [
                "Executar tarefa na \(.applicationName)",
                "Pedir à \(.applicationName) para executar uma tarefa"
            ],
            shortTitle: "Executar tarefa",
            systemImageName: "paperplane.fill"
        )
        AppShortcut(
            intent: GetMyraStatusIntent(),
            phrases: [
                "Consultar estado da \(.applicationName)",
                "Verificar estado da \(.applicationName)"
            ],
            shortTitle: "Consultar estado",
            systemImageName: "waveform.path"
        )
    }
}
