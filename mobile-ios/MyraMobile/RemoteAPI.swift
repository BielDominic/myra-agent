import Foundation
import Security
import Combine

struct RemoteTaskStatus: Decodable {
    let state: String
    let taskID: String?
    let objective: String?
    let currentStep: String?
    let stepNumber: Int
    let totalSteps: Int
    let result: String?
    let error: String?

    enum CodingKeys: String, CodingKey {
        case state
        case taskID = "task_id"
        case objective = "objetivo"
        case currentStep = "passo_atual"
        case stepNumber = "passo_num"
        case totalSteps = "passo_total"
        case result = "resultado"
        case error = "erro"
    }
}

private struct StartTaskPayload: Encodable {
    let objetivo: String
    let max_passos: Int
}

private struct APIErrorPayload: Decodable {
    let detail: String?
}

enum MyraRemoteError: LocalizedError {
    case invalidURL
    case missingToken
    case insecureRemoteURL
    case http(Int, String)
    case keychain(OSStatus)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Informe uma URL valida para a API remota."
        case .missingToken:
            return "Salve o token de acesso antes de conectar."
        case .insecureRemoteURL:
            return "Use HTTPS para acesso remoto. HTTP so e permitido em localhost."
        case let .http(code, detail):
            return "API MYRA (HTTP \(code)): \(detail)"
        case let .keychain(status):
            return "Nao foi possivel guardar o token no Keychain (\(status))."
        }
    }
}

@MainActor
final class RemoteAPI: ObservableObject {
    @Published private(set) var baseURL: String
    @Published private(set) var status: RemoteTaskStatus?
    @Published private(set) var isBusy = false
    @Published var errorMessage: String?

    private static let baseURLKey = "myra.remote.baseURL"

    init() {
        self.baseURL = UserDefaults.standard.string(forKey: Self.baseURLKey) ?? ""
    }

    var isConfigured: Bool {
        !baseURL.isEmpty && KeychainTokenStore.load() != nil
    }

    func saveConnection(baseURL rawURL: String, token rawToken: String) throws {
        let normalized = rawURL.trimmingCharacters(in: .whitespacesAndNewlines)
            .trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let token = rawToken.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let components = URLComponents(string: normalized),
              let scheme = components.scheme?.lowercased(),
              let host = components.host,
              !host.isEmpty,
              components.query == nil,
              components.fragment == nil else {
            throw MyraRemoteError.invalidURL
        }
        let isLoopback = ["localhost", "127.0.0.1", "::1"].contains(host.lowercased())
        guard scheme == "https" || (scheme == "http" && isLoopback) else {
            throw MyraRemoteError.insecureRemoteURL
        }
        guard !token.isEmpty else { throw MyraRemoteError.missingToken }

        try KeychainTokenStore.save(token)
        baseURL = normalized
        UserDefaults.standard.set(normalized, forKey: Self.baseURLKey)
        errorMessage = nil
    }

    func refreshStatus() async {
        guard isConfigured, !isBusy else { return }
        isBusy = true
        defer { isBusy = false }
        do {
            let data = try await request(path: "status", method: "GET")
            status = try JSONDecoder().decode(RemoteTaskStatus.self, from: data)
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func startTask(objective: String) async {
        let trimmed = objective.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            errorMessage = "Descreva a tarefa antes de enviar."
            return
        }
        guard trimmed.count <= 1200 else {
            errorMessage = "O limite do objetivo e 1.200 caracteres."
            return
        }
        guard isConfigured, !isBusy else { return }

        isBusy = true
        defer { isBusy = false }
        do {
            let body = try JSONEncoder().encode(StartTaskPayload(objetivo: trimmed, max_passos: 30))
            _ = try await request(path: "task", method: "POST", body: body)
            errorMessage = nil
            await refreshStatusAfterAction()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func cancelTask() async {
        guard isConfigured, !isBusy else { return }
        isBusy = true
        defer { isBusy = false }
        do {
            _ = try await request(path: "cancel", method: "POST")
            errorMessage = nil
            await refreshStatusAfterAction()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func refreshStatusAfterAction() async {
        do {
            let data = try await request(path: "status", method: "GET")
            status = try JSONDecoder().decode(RemoteTaskStatus.self, from: data)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func request(path: String, method: String, body: Data? = nil) async throws -> Data {
        guard let url = URL(string: baseURL + "/" + path),
              let token = KeychainTokenStore.load() else {
            throw MyraRemoteError.missingToken
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 30
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw MyraRemoteError.http(-1, "Resposta de rede invalida.")
        }
        guard (200..<300).contains(http.statusCode) else {
            let detail = (try? JSONDecoder().decode(APIErrorPayload.self, from: data).detail)
                ?? String(data: data, encoding: .utf8)
                ?? "Falha sem detalhes."
            throw MyraRemoteError.http(http.statusCode, detail)
        }
        return data
    }
}

enum KeychainTokenStore {
    private static let service = "com.myra.mobile.remote-api"
    private static let account = "bearer-token"

    static func load() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess,
              let data = item as? Data,
              let token = String(data: data, encoding: .utf8) else {
            return nil
        }
        return token
    }

    static func save(_ token: String) throws {
        let key: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        let data = Data(token.utf8)
        let update: [String: Any] = [kSecValueData as String: data]
        let status = SecItemUpdate(key as CFDictionary, update as CFDictionary)
        if status == errSecItemNotFound {
            var add = key
            add[kSecValueData as String] = data
            add[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
            let addStatus = SecItemAdd(add as CFDictionary, nil)
            guard addStatus == errSecSuccess else { throw MyraRemoteError.keychain(addStatus) }
        } else if status != errSecSuccess {
            throw MyraRemoteError.keychain(status)
        }
    }
}
