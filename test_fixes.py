from api.models.analysis_models import GraphEditRequest
from utils.security import encrypt_string, decrypt_string

def test_graph_edit():
    print("\n--- Testing GraphEditRequest ---")
    try:
        GraphEditRequest(action="add_node")
        assert False, "Should have raised ValueError for missing node_id"
    except ValueError:
        pass
        
    try:
        GraphEditRequest(action="add_edge", source="A")
        assert False, "Should have raised ValueError for missing target"
    except ValueError:
        pass

    try:
        GraphEditRequest(action="update_node", node_id="A")
        assert False, "Should have raised ValueError for missing updates"
    except ValueError:
        pass
        
    # Valid one
    try:
        GraphEditRequest(action="add_node", node_id="A")
    except Exception as e:
        assert False, f"Failed valid add_node: {e}"

def test_encryption():
    print("\n--- Testing Encryption ---")
    secret = "my_super_secret_totp_seed"
    enc = encrypt_string(secret)
    dec = decrypt_string(enc)
    
    assert enc != secret, "Encryption failed: encrypted string equals plain secret"
    assert dec == secret, "Decryption failed: decrypted string does not match original secret"
    print("✅ All assertions passed successfully!")

if __name__ == "__main__":
    test_graph_edit()
    test_encryption()
