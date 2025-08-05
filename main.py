# SITE NÃO ESTÁ PRONTO! Necessita de vários ajustes. Colocando todo meu conhecimento a jogo

# Estou procurando estágio, Região Metropolitana do RS ("grande Porto Alegre")
# Me chamo João e tenho 17 anos


from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import pyodbc
import funcoes as fun
from twilio.rest import Client
from dotenv import load_dotenv 
import os


load_dotenv()

dados_conexao = ("Driver={SQLite3 ODBC Driver};"
                 "Server=localhost;"
                 "Database=usuarios.db")


app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.urandom(24)



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


# No momento, função em espera
@app.route("/recuperacao_senha", methods=['POST'])
def handle_esqueciSenha():
    if request.method == "POST":
        cpf = request.form["cpf"]
        print("---Tentativa de Trocar Senha---")
        print(f"CPF: {cpf}")
    
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
# --- Rota da Tabela de Mensalidades ---
@app.route("/mensalidade") 
def mensalidade():
    dados_mensalidades_processados = [] 
    mensagem = None
    erro_bd = None
    erro_geral = None

    try:
        with pyodbc.connect(dados_conexao) as conexao:
            with conexao.cursor() as cursor:
                comando = """SELECT nome, cpf, jan, fev, mar, abr, mai, jun, jul, ago, set_, out, nov, dec
                             FROM mensalidade"""

                cursor.execute(comando)
                resultados = cursor.fetchall()
                print(f"Resultados brutos do banco de dados: {resultados}")

                if not resultados:
                    mensagem = "Nenhum registro de mensalidade encontrado."
                else:
                    
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
                  
                    status_atual = status_atual_bytes.decode('utf-8') if isinstance(status_atual_bytes, bytes) else status_atual_bytes
                    
                    
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

@app.route("/biblioteca", methods=["GET"])
def biblioteca():
    livros = [] # Inicializa uma lista vazia para armazenar os livros
    mensagem = None
    try:
        conexao = pyodbc.connect(dados_conexao)
        cursor = conexao.cursor()

        # Seleciona todos os livros
        cursor.execute("SELECT titulo, autor, ano_publicacao, disponivel FROM livros")
        resultados = cursor.fetchall() # Pega TODOS os resultados

        if not resultados:
            mensagem = "Nenhum livro cadastrado ainda."
        else:
            for livro_bruto in resultados:
                # Cada 'livro_bruto' é uma tupla como (titulo, autor, ano_publicacao, disponivel)
                # O 'disponivel' é um valor booleano ou numérico (0/1).
                # Você pode convertê-lo para "True" / "False" para exibir.
                disponivel_str = "Disponível" if livro_bruto[3] == 1 else "Indisponível"
                
                livros.append({
                    "titulo": livro_bruto[0].decode('utf-8') if isinstance(livro_bruto[0], bytes) else livro_bruto[0],
                    "autor": livro_bruto[1].decode('utf-8') if isinstance(livro_bruto[1], bytes) else livro_bruto[1],
                    "ano_publicacao": livro_bruto[2],
                    "disponivel": disponivel_str,
                    "is_disponivel_bool": True if livro_bruto[3] == 1 else False # Adiciona um booleano para a lógica do botão
                })
        
    except pyodbc.Error as ex:
        print(f"Erro de Banco de Dados ao buscar livros: {ex}")
        mensagem = "Ocorreu um erro ao carregar os livros. Tente novamente mais tarde."
    finally:
        if 'conexao' in locals() and conexao:
            conexao.close()
            print("Conexão com o banco de dados fechada após busca de livros.")

    # Passa a lista de livros para o template
    return render_template("menu/biblioteca.html", 
                           ano_atual=fun.ano_atual(), 
                           livros=livros)

@app.route("/cadastrar_livro", methods=["POST"])
def handle_cadastrar_livro():
    if request.method == "POST":
        titulo = request.form["title"]
        autor = request.form["author"]
        anoPublicacao = request.form["year"]
        data_atual = fun.dataAtual()

        print("--- Cadastro de Novo Livro ---")
        print(f"Título: {titulo}")
        print(f"Autor: {autor}")
        print(f"Ano Publicação: {anoPublicacao}")
        print(f"Ano Atual: {data_atual}")

        try:
            conexao = pyodbc.connect(dados_conexao)
            cursor = conexao.cursor()
            comando = "INSERT INTO livros (titulo, autor, ano_publicacao, data_cadastro) VALUES (?, ?, ?, ?)"
            cursor.execute(comando, (titulo, autor, anoPublicacao, data_atual))
            conexao.commit()
            flash("Livro cadastrado com sucesso!", "success")
            
        except pyodbc.Error as ex:
            print(f"Erro ao cadastrar livro: {ex}")
            flash("Ocorreu um erro ao cadastrar o livro. Tente novamente.", "danger")
        finally:
            if 'conexao' in locals() and conexao:
                conexao.close()


        flash("Livro cadastrado (simulado por enquanto)! Redirecionando...", "success")
        return redirect(url_for('biblioteca'))

          

if __name__ == '__main__':
    app.run(debug=True)
