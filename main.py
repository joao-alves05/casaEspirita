# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import pyodbc
import funcoes as fun # Assumindo que 'funcoes.py' existe e contém as funções referenciadas
from twilio.rest import Client # Assumindo que Twilio é usado em outras partes do app
from dotenv import load_dotenv # Assumindo que dotenv é usado em outras partes do app
import os

# Carrega variáveis de ambiente (se você tiver um arquivo .env)
load_dotenv()

# Configuração da conexão com o banco de dados
dados_conexao = ("Driver={SQLite3 ODBC Driver};"
                 "Server=localhost;"
                 "Database=usuarios.db") # Usando o banco de dados 'usuarios.db' fornecido

# Crie a instância do Flask e diga a ele onde estão os arquivos estáticos
app = Flask(__name__, static_folder='static')

app.config['SECRET_KEY'] = os.urandom(24)


# Variável global para armazenar o CPF (se estiver usando uma, cuidado com concorrência em produção)
# Em aplicações Flask reais, geralmente se usa sessões para armazenar dados de usuário
# Para este exemplo, vamos manter como está, mas ciente das limitações em um ambiente multi-usuário.
cpfGlobal_mensalidade = [] # Será uma lista com o CPF do usuário logado


# --- Rotas Existentes ---
@app.route("/")
def paginaInicial():
    return render_template("paginaInicial.html")

@app.route("/entrar")
def entrar():
    return render_template("conta/entrar.html")


@app.route("/entrar", methods=["POST"])
def handle_login():
    cpf = request.form["cpf"]
    password = request.form["password"]
    
    # Limpa a lista antes de adicionar o novo CPF para garantir que só haja um
    global cpfGlobal_mensalidade
    cpfGlobal_mensalidade.clear()
    cpfGlobal_mensalidade.append(cpf)
    
    print("---Tentativa de login---")
    print(f"CPF: {cpf}")

    conexao = None
    try:
        conexao = pyodbc.connect(dados_conexao)
        cursor = conexao.cursor()

        cursor.execute("SELECT senha FROM usuarios WHERE cpf = ?", (cpf,))
        resultado = cursor.fetchone()

        aprovado = False
        if resultado:
            senha_usuario = resultado[0]
            if password == senha_usuario:
                aprovado = True
            else:
                aprovado = False

        if aprovado:
            flash("Login bem-sucedido!", "success")
            return redirect(url_for('menu'))
        else:
            flash("CPF ou senha inválidos. Tente novamente.", "danger")
            return redirect(url_for('entrar'))

    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        print(f"Erro de Banco de Dados: {ex}")
        flash("Ocorreu um erro ao tentar entrar. Tente novamente mais tarde.", "danger")
        return redirect(url_for('entrar'))
    finally:
        if conexao:
            conexao.close()
            print("Conexão com o banco de dados fechada.")

@app.route("/recuperacao_senha")
def esqueciSenha():
    return render_template("conta/esqueciSenha.html")

@app.route("/recuperacao_senha", methods=['POST'])
def handle_esqueciSenha():
    if request.method == "POST":
        cpf = request.form["cpf"]
        print("---Tentativa de Trocar Senha---")
        print(f"CPF: {cpf}")
        # O código Twilio e de geração de token está comentado aqui,
        # mas seria o local para integrá-lo se necessário.
        return render_template("conta/entrar.html")

@app.route("/token")
def esqueciSenha_token():
    return render_template("conta/token.html")

@app.route("/cadastrarSe")
def cadastrarSe():
    return render_template("conta/cadastrar.html")

@app.route("/cadastrarSe", methods=["POST"])
def handle_cadastrarSe():
    if request.method == "POST":
        full_name = request.form["full_name"]
        telefone_bruto = request.form["telefone"]
        telefone_formatado = fun.formatar_telefone(telefone_bruto)
        cpf = request.form["cpf"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]
        data_criacao = fun.dataAtual()
        ano = fun.ano_atual()

        print("---Tentativa de Cadastro---")
        print(f"Nome Completo: {full_name}")
        print(f"Telefone: {telefone_formatado}")
        print(f"CPF: {cpf}")
        print(f"Senha: {new_password}")
        print(f"Confirmar Senha: {confirm_password}")
        print(f"Data Criação: {data_criacao}")

        if new_password != confirm_password:
            flash("As senhas não coincidem. Tente novamente.", "danger")
            return redirect(url_for('cadastrarSe'))

        try:
            conexao = pyodbc.connect(dados_conexao)
            cursor = conexao.cursor()

            # Inserir na tabela de usuários
            comando1 = 'INSERT INTO usuarios (nome, cpf, senha, telefone, data_criacao) VALUES (?, ?, ?, ?, ?)'
            cursor.execute(comando1, (full_name, cpf, new_password, telefone_formatado, data_criacao))

            # Inserir na tabela de mensalidade com valores padrão
            # Assumindo que as colunas de mês (jan, fev, etc.) têm um valor padrão 'FALSE' no schema do DB
            comando2 = 'INSERT INTO mensalidade (nome, cpf, ano) VALUES (?, ?, ?)'
            cursor.execute(comando2, (full_name, cpf, ano))
            conexao.commit()
            print("Comando de cadastro e inicialização de mensalidade funcionou! _____________________________________________________________________")

            flash("Cadastro realizado com sucesso! Agora você pode fazer login.", "success")
            return redirect(url_for('entrar'))

        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            print(f"Erro de Banco de Dados: {ex}")
            flash("Ocorreu um erro ao tentar cadastrar. Tente novamente mais tarde.", "danger")
            return redirect(url_for('cadastrarSe'))
        finally:
            if 'conexao' in locals() and conexao:
                conexao.close()
                print("Conexão com o banco de dados fechada.")

@app.route("/menu")
def menu():
    return render_template("menu/menu.html")

print(cpfGlobal_mensalidade)
# --- Rota da Tabela de Mensalidades (ATUALIZADA) ---
@app.route("/mensalidade") # Esta rota agora buscará e exibirá os dados da tabela
def mensalidade():
    dados_mensalidades_processados = [] # Renomeado para clareza
    mensagem = None
    erro_bd = None
    erro_geral = None

    try:
        with pyodbc.connect(dados_conexao) as conexao:
            with conexao.cursor() as cursor:
                # Seleciona o nome, CPF e o status dos meses
                # IMPORTANTE: Adicione 'cpf' à seleção para que possa ser usado no botão de atualização
                # E use 'set_' para a coluna 'set' devido à palavra reservada
                comando = """SELECT nome, cpf, jan, fev, mar, abr, mai, jun, jul, ago, set_, out, nov, dec
                             FROM mensalidade"""

                cursor.execute(comando)
                resultados = cursor.fetchall()
                print(f"Resultados brutos do banco de dados: {resultados}")

                if not resultados:
                    mensagem = "Nenhum registro de mensalidade encontrado."
                else:
                    # Nomes das colunas na ordem em que são retornadas pela query (incluindo 'cpf')
                    colunas = ['nome', 'cpf', 'jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']

                    for linha_bruta in resultados:
                        linha_processada = {}
                        for i, valor in enumerate(linha_bruta):
                            # Decodifica strings de bytes para strings normais
                            if isinstance(valor, bytes):
                                linha_processada[colunas[i]] = valor.decode('utf-8')
                            else:
                                linha_processada[colunas[i]] = valor
                        dados_mensalidades_processados.append(linha_processada)

                    print(f"Dados de mensalidade processados para o template: {dados_mensalidades_processados}")

    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        print(f"Erro no banco de dados: {ex}")
        if "syntax error" in str(ex).lower() and "set" in str(ex).lower():
            erro_bd = "Erro de sintaxe SQL na coluna 'set'. Certifique-se de que 'set_' está sendo usado e que o nome da coluna está escapado corretamente para o seu DB (ex: \"set_\")."
        else:
            erro_bd = f"Ocorreu um erro ao buscar as mensalidades no banco de dados: {ex}"
        
    except Exception as e:
        print(f"Erro inesperado: {e}")
        erro_geral = f"Ocorreu um erro inesperado ao carregar as mensalidades: {e}"
    
    # Renderiza o template com os dados processados e as mensagens
    return render_template('menu/mensalidade.html', 
                           dados_mensalidades=dados_mensalidades_processados,
                           mensagem=mensagem,
                           erro_bd=erro_bd,
                           erro_geral=erro_geral)


# --- Rota para Atualizar Mensalidade (Exemplo - você precisará implementar a lógica de UPDATE) ---
@app.route("/atualizar_mensalidade/<cpf>/<int:mes_index>")
def atualizar_mensalidade(cpf, mes_index):
    # Mapeia o índice do mês para o nome da coluna no banco de dados
    # Lembre-se que 'set' é 'set_' no DB
    meses_nomes = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set_', 'out', 'nov', 'dec']
    nome_mes = meses_nomes[mes_index]

    try:
        with pyodbc.connect(dados_conexao) as conexao:
            with conexao.cursor() as cursor:
                # Primeiro, obtenha o status atual do mês
                comando_select = f"SELECT {nome_mes} FROM mensalidade WHERE cpf = ?"
                cursor.execute(comando_select, (cpf,))
                resultado_atual = cursor.fetchone()

                if resultado_atual:
                    status_atual_bytes = resultado_atual[0]
                    # Decodifica o status atual (b'TRUE' ou b'FALSE')
                    status_atual = status_atual_bytes.decode('utf-8') if isinstance(status_atual_bytes, bytes) else status_atual_bytes
                    
                    # Inverte o status: 'TRUE' para 'FALSE', 'FALSE' para 'TRUE'
                    novo_status = 'TRUE' if status_atual == 'FALSE' else 'FALSE'
                    
                    # Atualiza o status no banco de dados
                    comando_update = f"UPDATE mensalidade SET {nome_mes} = ? WHERE cpf = ?"
                    cursor.execute(comando_update, (novo_status, cpf))
                    conexao.commit()
                    flash(f"Status de {nome_mes} para {cpf} atualizado para {novo_status}.", "success")
                else:
                    flash(f"CPF {cpf} não encontrado para atualização.", "danger")

    except pyodbc.Error as ex:
        print(f"Erro ao atualizar mensalidade: {ex}")
        flash(f"Erro ao atualizar o status de {nome_mes} para o CPF {cpf}.", "danger")
    except Exception as e:
        print(f"Erro inesperado ao atualizar mensalidade: {e}")
        flash("Ocorreu um erro inesperado ao atualizar a mensalidade.", "danger")

    return redirect(url_for('mensalidade')) # Redireciona de volta para a tabela


# --- Outras Rotas ---
@app.route("/despesas")
def despesas():
    return render_template("menu/despesas.html")

@app.route("/devedores")
def devedores():
    return render_template("menu/devedores.html")

@app.route("/biblioteca")
def biblioteca():
    return render_template("menu/biblioteca.html")

if __name__ == '__main__':
    app.run(debug=True)
