from csr_ir.protocol import assert_protocol


if __name__ == "__main__":
    assert_protocol("configs/benchmarks.yaml", "configs/data_protocol.yaml")
    print("protocol: PASS")
